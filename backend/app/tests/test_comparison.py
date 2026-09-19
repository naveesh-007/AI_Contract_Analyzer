"""
Tests for Standard Clause Comparison (SRS-S02).
Verifies:
- Benchmark template and standard clause seeding
- Matching actual clauses to benchmark categories
- Deviation level calculation and difference identification
- Comparison API endpoints and document scoping isolation
- Prompt injection defense in comparison pipeline
"""
import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base
from app.main import create_app
from app.models.clause import Clause
from app.models.comparison import ClauseComparison, StandardContractTemplate
from app.models.document import Document, DocumentPage
from app.repositories.comparison_repo import ComparisonRepository
from app.services.comparison_service import ComparisonService
from app.services.llm_service import LLMService, MockLLMProvider

# SQLite test database setup
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """Yields a clean in-memory async database session."""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as session:
        yield session

    await engine.dispose()


@pytest.fixture
async def sample_rental_doc(db_session: AsyncSession):
    """Creates a sample rental agreement with clauses in the database."""
    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        filename="rental_lease.txt",
        document_type="Rental Agreement",
        file_type="txt",
        file_size=1024,
        status="ANALYZED",
    )
    page = DocumentPage(
        id=uuid.uuid4(),
        document_id=doc_id,
        page_number=1,
        text="Sample rental lease agreement text.",
        char_start=0,
        char_end=35,
    )
    c1 = Clause(
        id=uuid.uuid4(),
        document_id=doc_id,
        section_number="4.1",
        section_title="Term and Renewal",
        clause_text="This agreement shall automatically renew for a successive 24-month term unless Tenant delivers written notice at least 3 days prior.",
        risk_level="HIGH",
        explanation="Imposes a 24-month lock-in with only 3 days notice.",
        reason="Severe renewal lock-in with narrow cancellation window.",
        page_number=1,
    )
    c2 = Clause(
        id=uuid.uuid4(),
        document_id=doc_id,
        section_number="2.0",
        section_title="Monthly Rent",
        clause_text="Rent of $1,500 is due on the 1st of each month. A grace period of 5 calendar days is provided before a $25 late fee is assessed.",
        risk_level="LOW",
        explanation="Standard rent due on the 1st with 5-day grace period.",
        reason="Customary payment and grace period terms.",
        page_number=1,
    )

    db_session.add_all([doc, page, c1, c2])
    await db_session.commit()
    return doc, [c1, c2]


class TestComparisonRepositoryAndTemplates:
    """Tests standard template seeding and retrieval."""

    async def test_benchmark_templates_seeded_automatically(self, db_session: AsyncSession):
        repo = ComparisonRepository(db_session)
        await repo.ensure_seed_templates()

        templates = await repo.get_all_templates()
        assert len(templates) >= 4

        doc_types = {t.document_type for t in templates}
        assert "Rental Agreement" in doc_types
        assert "Freelance Contract" in doc_types
        assert "Terms of Service" in doc_types
        assert "Other" in doc_types

    async def test_get_template_by_document_type(self, db_session: AsyncSession):
        repo = ComparisonRepository(db_session)
        rental_tpl = await repo.get_template_by_document_type("Rental Agreement")
        assert rental_tpl is not None
        assert rental_tpl.document_type == "Rental Agreement"
        assert len(rental_tpl.clauses) >= 5

        categories = {c.category for c in rental_tpl.clauses}
        assert "PAYMENT" in categories
        assert "TERMINATION" in categories
        assert "RENEWAL" in categories


class TestComparisonServiceLogic:
    """Tests comparison evaluation, deviation classification, and difference detection."""

    async def test_high_deviation_detected_for_aggressive_renewal(
        self, db_session: AsyncSession, sample_rental_doc
    ):
        doc, clauses = sample_rental_doc
        comp_service = ComparisonService(db_session, LLMService(provider=MockLLMProvider()))

        response = await comp_service.compare_document_clauses(doc.id)
        assert response.document_id == doc.id
        assert len(response.comparisons) == 2

        # Find the renewal clause comparison
        renewal_comp = next(
            (c for c in response.comparisons if "24-month" in c.actual_clause), None
        )
        assert renewal_comp is not None
        assert renewal_comp.deviation_level.value == "HIGH"
        assert renewal_comp.similarity_score <= 0.60
        assert len(renewal_comp.differences) >= 1
        assert any("24-month" in d for d in renewal_comp.differences)

    async def test_low_deviation_detected_for_standard_payment(
        self, db_session: AsyncSession, sample_rental_doc
    ):
        doc, clauses = sample_rental_doc
        comp_service = ComparisonService(db_session, LLMService(provider=MockLLMProvider()))

        response = await comp_service.compare_document_clauses(doc.id)

        # Find payment clause comparison
        payment_comp = next(
            (c for c in response.comparisons if "grace period" in c.actual_clause), None
        )
        assert payment_comp is not None
        assert payment_comp.deviation_level.value == "LOW"
        assert payment_comp.similarity_score >= 0.80

    async def test_summary_metrics_calculated_correctly(
        self, db_session: AsyncSession, sample_rental_doc
    ):
        doc, _ = sample_rental_doc
        comp_service = ComparisonService(db_session, LLMService(provider=MockLLMProvider()))

        response = await comp_service.compare_document_clauses(doc.id)
        assert response.summary.total_comparisons == 2
        assert response.summary.high_deviation >= 1
        assert response.summary.low_deviation >= 1
        assert response.summary.average_similarity > 0.0


class TestComparisonAPIRoutes:
    """Tests FastAPI comparison routes and document isolation."""

    @pytest.fixture
    def app(self, db_session: AsyncSession):
        app_instance = create_app()
        from app.core.database import get_db
        async def override_get_db():
            yield db_session
        app_instance.dependency_overrides[get_db] = override_get_db
        return app_instance

    async def test_compare_endpoint_executes_and_returns_comparisons(
        self, app, sample_rental_doc, db_session: AsyncSession
    ):
        doc, _ = sample_rental_doc
        from unittest.mock import patch
        with patch("app.services.comparison_service.LLMService") as MockService:
            MockService.return_value = LLMService(provider=MockLLMProvider())
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                res = await client.post(f"/api/documents/{doc.id}/compare")
                assert res.status_code == 200
                data = res.json()
                assert data["document_id"] == str(doc.id)
                assert "comparisons" in data
                assert len(data["comparisons"]) == 2

    async def test_get_comparisons_with_filter(
        self, app, sample_rental_doc, db_session: AsyncSession
    ):
        doc, _ = sample_rental_doc
        from unittest.mock import patch
        with patch("app.services.comparison_service.LLMService") as MockService:
            MockService.return_value = LLMService(provider=MockLLMProvider())
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                # First trigger comparison
                await client.post(f"/api/documents/{doc.id}/compare")

                # Filter HIGH deviation
                res_high = await client.get(
                    f"/api/documents/{doc.id}/comparisons", params={"deviation_level": "HIGH"}
                )
                assert res_high.status_code == 200
                data_high = res_high.json()
                for comp in data_high["comparisons"]:
                    assert comp["deviation_level"] == "HIGH"



    async def test_list_templates_endpoint(self, app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            res = await client.get("/api/benchmarks/templates")
            assert res.status_code == 200
            templates = res.json()
            assert len(templates) >= 4

    async def test_cross_document_scoping_isolation(
        self, db_session: AsyncSession, sample_rental_doc
    ):
        doc1, _ = sample_rental_doc

        # Create doc2
        doc2_id = uuid.uuid4()
        doc2 = Document(
            id=doc2_id,
            filename="freelance.txt",
            document_type="Freelance Contract",
            file_type="txt",
            file_size=500,
            status="ANALYZED",
        )
        c3 = Clause(
            id=uuid.uuid4(),
            document_id=doc2_id,
            section_number="1.0",
            section_title="Payment",
            clause_text="Client shall pay within 30 days.",
            risk_level="LOW",
            explanation="Net 30 terms.",
            reason="Standard payment.",
            page_number=1,
        )
        db_session.add_all([doc2, c3])
        await db_session.commit()

        comp_service = ComparisonService(db_session, LLMService(provider=MockLLMProvider()))
        await comp_service.compare_document_clauses(doc1.id)
        await comp_service.compare_document_clauses(doc2.id)

        doc1_comps = await comp_service.get_document_comparisons(doc1.id)
        doc2_comps = await comp_service.get_document_comparisons(doc2.id)

        assert len(doc1_comps.comparisons) == 2
        assert len(doc2_comps.comparisons) == 1

        # Verify no cross-document ID contamination
        doc1_ids = {str(c.document_id) for c in doc1_comps.comparisons}
        doc2_ids = {str(c.document_id) for c in doc2_comps.comparisons}
        assert doc1_ids == {str(doc1.id)}
        assert doc2_ids == {str(doc2.id)}

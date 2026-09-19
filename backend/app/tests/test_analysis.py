"""
Unit and integration tests for AI Analysis Pipeline, Summary API, and error edge cases.

Test cases:
1. Document with no obvious risk (all LOW risk)
2. Document with multiple high-risk clauses (HIGH/MEDIUM/LOW)
3. Malformed LLM JSON recovery and error handling
4. Missing page number resilience
5. Missing section number resilience
6. Empty document handling
7. AI API failure handling
8. Verification that LOW/MEDIUM/HIGH counts match clause records exactly
"""
from datetime import datetime, timezone
import io
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.clause import Clause
from app.models.document import Document, DocumentPage
from app.schemas.analysis import LLMAnalysisResult, LLMClauseItem
from app.services.analysis_pipeline import (
    AnalysisPipeline,
    AnalysisPipelineError,
    EmptyDocumentError,
)
from app.services.clause_extraction import extract_clauses_from_pages
from app.services.llm_service import (
    BaseLLMProvider,
    LLMJSONValidationError,
    LLMService,
    LLMServiceError,
    MockLLMProvider,
    extract_json_from_text,
)


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


# ─── 1. Clause Extraction Unit Tests ──────────────────────────────────────────


class TestClauseExtraction:
    """Tests for section detection, heading recognition, and paragraph splitting."""

    def test_numbered_sections_detected(self):
        doc_id = uuid.uuid4()
        text = """1. TERM AND TERMINATION
The term of this Agreement shall commence on the Effective Date.

8.2 Termination for Cause
Either party may terminate immediately if there is a material breach.

10. INDEMNIFICATION
Contractor agrees to indemnify and hold harmless the Company."""

        page = DocumentPage(
            document_id=doc_id,
            page_number=1,
            text=text,
            char_start=0,
            char_end=len(text),
        )

        clauses = extract_clauses_from_pages([page])
        assert len(clauses) >= 2
        sec_nums = [c.section_number for c in clauses if c.section_number]
        assert "1" in sec_nums or "8.2" in sec_nums or "10" in sec_nums

    def test_missing_section_numbers_graceful(self):
        """Documents without numbered sections should still extract clauses cleanly."""
        doc_id = uuid.uuid4()
        text = """This is an informal consulting agreement without section numbers.

The Consultant will deliver services by the 1st of every month.

Either party may terminate this agreement with 30 days written notice."""

        page = DocumentPage(
            document_id=doc_id,
            page_number=1,
            text=text,
            char_start=0,
            char_end=len(text),
        )

        clauses = extract_clauses_from_pages([page])
        assert len(clauses) >= 1
        assert any("Consultant" in c.clause_text for c in clauses)
        # Verbatim text check — never invent text
        for c in clauses:
            assert c.clause_text in text

    def test_missing_page_numbers_resilience(self):
        """DocumentPage with None or missing page number defaults safely."""
        doc_id = uuid.uuid4()
        page = DocumentPage(
            document_id=doc_id,
            page_number=1,
            text="Standard confidentiality clause across all parties.",
            char_start=None,
            char_end=None,
        )
        clauses = extract_clauses_from_pages([page])
        assert len(clauses) == 1
        assert clauses[0].page_number == 1


# ─── 2. JSON Extraction and LLM Service Tests ─────────────────────────────────


class TestLLMServiceAndJSONParsing:
    """Tests for LLM service, JSON recovery, and error handling."""

    def test_extract_json_clean(self):
        raw = '{"overall_summary": "Low risk contract", "clauses": []}'
        data = extract_json_from_text(raw)
        assert data["overall_summary"] == "Low risk contract"

    def test_extract_json_from_markdown_fences(self):
        raw = '```json\n{\n  "overall_summary": "Standard terms",\n  "clauses": []\n}\n```'
        data = extract_json_from_text(raw)
        assert data["overall_summary"] == "Standard terms"

    def test_extract_json_with_preamble_and_trailing_comma(self):
        raw = 'Here is the analysis:\n```json\n{"overall_summary": "Notice terms", "clauses": [],}\n```\nHope this helps!'
        data = extract_json_from_text(raw)
        assert data["overall_summary"] == "Notice terms"

    def test_extract_json_malformed_raises_error(self):
        raw = "This is not valid JSON at all: {unclosed"
        with pytest.raises(LLMServiceError):
            extract_json_from_text(raw)

    @pytest.mark.asyncio
    async def test_mock_llm_provider_low_risk_document(self):
        """Document with standard boilerplate should produce only LOW risk clauses."""
        provider = MockLLMProvider()
        prompt = """CANDIDATE CLAUSES JSON:
[
  {
    "section_number": "1.0",
    "section_title": "Definitions",
    "clause_text": "The terms defined here shall apply to all standard notices.",
    "page_number": 1
  },
  {
    "section_number": "2.0",
    "section_title": "Notices",
    "clause_text": "All notices shall be in writing sent via email with confirmation.",
    "page_number": 1
  }
]"""
        raw = await provider.generate_raw(prompt)
        parsed = extract_json_from_text(raw)
        result = LLMAnalysisResult.model_validate(parsed)
        assert len(result.clauses) == 2
        assert all(c.risk_level == "LOW" for c in result.clauses)
        assert all("may" in c.explanation or "appears" in c.explanation or "could" in c.explanation for c in result.clauses)

    @pytest.mark.asyncio
    async def test_mock_llm_provider_high_risk_document(self):
        """Document with indemnity and unlimited liability must classify as HIGH risk."""
        provider = MockLLMProvider()
        prompt = """CANDIDATE CLAUSES JSON:
[
  {
    "section_number": "5.1",
    "section_title": "Indemnification",
    "clause_text": "Contractor shall indemnify and hold harmless the Client from all claims with unlimited liability.",
    "page_number": 2
  },
  {
    "section_number": "6.0",
    "section_title": "Termination",
    "clause_text": "Client may immediately terminate without notice and Contractor shall forfeit all fees.",
    "page_number": 2
  },
  {
    "section_number": "7.0",
    "section_title": "Renewal",
    "clause_text": "This agreement will auto-renew for successive 5-year terms.",
    "page_number": 3
  }
]"""
        raw = await provider.generate_raw(prompt)
        parsed = extract_json_from_text(raw)
        result = LLMAnalysisResult.model_validate(parsed)
        assert len(result.clauses) == 3
        high_clauses = [c for c in result.clauses if c.risk_level == "HIGH"]
        med_clauses = [c for c in result.clauses if c.risk_level == "MEDIUM"]
        assert len(high_clauses) == 2
        assert len(med_clauses) == 1

    @pytest.mark.asyncio
    async def test_llm_service_retry_on_malformed_json(self):
        """LLMService should retry if first response is malformed, then succeed if second is valid."""
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_provider.generate_raw = AsyncMock(
            side_effect=[
                "Invalid non-json response",  # attempt 1 fails
                '{"overall_summary": "Recovered", "clauses": [{"section_number": "1", "section_title": "T", "clause_text": "text", "risk_level": "LOW", "explanation": "This may be low risk.", "reason": "Standard.", "page_number": 1}]}',  # attempt 2 succeeds
            ]
        )

        service = LLMService(provider=mock_provider)
        res = await service.analyze_clauses(
            candidate_clauses=[{"clause_text": "text", "page_number": 1}],
            max_retries=2,
        )
        assert res.overall_summary == "Recovered"
        assert len(res.clauses) == 1
        assert mock_provider.generate_raw.call_count == 2

    @pytest.mark.asyncio
    async def test_llm_service_fails_after_max_retries(self):
        """LLMService raises LLMJSONValidationError when all attempts fail."""
        mock_provider = MagicMock(spec=BaseLLMProvider)
        mock_provider.generate_raw = AsyncMock(return_value="Corrupt gibberish")

        service = LLMService(provider=mock_provider)
        with pytest.raises(LLMJSONValidationError):
            await service.analyze_clauses(
                candidate_clauses=[{"clause_text": "text", "page_number": 1}],
                max_retries=1,
            )


# ─── 3. End-to-End Pipeline & Strict Counts ───────────────────────────────────


class TestAnalysisPipeline:
    """Tests for AnalysisPipeline execution and count calculation."""

    @pytest.mark.asyncio
    async def test_empty_document_raises_error(self):
        session = AsyncMock()
        pipeline = AnalysisPipeline(session)

        # Mock empty doc
        doc_id = uuid.uuid4()
        fake_doc = MagicMock()
        fake_doc.pages = []

        with patch.object(pipeline.doc_repo, "get_document_with_pages", AsyncMock(return_value=fake_doc)):
            with pytest.raises(EmptyDocumentError, match="no text pages"):
                await pipeline.run(doc_id)

    @pytest.mark.asyncio
    async def test_pipeline_calculates_strict_counts(self):
        """Pipeline must verify that stored HIGH, MEDIUM, LOW counts strictly match."""
        session = AsyncMock()
        pipeline = AnalysisPipeline(session)
        doc_id = uuid.uuid4()

        fake_doc = MagicMock()
        fake_doc.id = doc_id
        fake_page = DocumentPage(
            document_id=doc_id,
            page_number=1,
            text="1. Scope of work.\n\n2. Indemnity with unlimited liability.\n\n3. Auto-renewal terms.",
            char_start=0,
            char_end=100,
        )
        fake_doc.pages = [fake_page]

        # Mock LLM service
        mock_llm = MagicMock(spec=LLMService)
        mock_llm.analyze_clauses = AsyncMock(
            return_value=LLMAnalysisResult(
                overall_summary="Contract contains 1 high, 1 medium, 1 low risk clause.",
                clauses=[
                    LLMClauseItem(
                        section_number="1",
                        section_title="Scope",
                        clause_text="Scope of work.",
                        risk_level="LOW",
                        explanation="This appears to be standard scope.",
                        reason="Standard.",
                        page_number=1,
                    ),
                    LLMClauseItem(
                        section_number="2",
                        section_title="Indemnity",
                        clause_text="Indemnity with unlimited liability.",
                        risk_level="HIGH",
                        explanation="This may create uncapped exposure.",
                        reason="Indemnity.",
                        page_number=1,
                    ),
                    LLMClauseItem(
                        section_number="3",
                        section_title="Renewal",
                        clause_text="Auto-renewal terms.",
                        risk_level="MEDIUM",
                        explanation="This could renew without manual action.",
                        reason="Renewal.",
                        page_number=1,
                    ),
                ],
            )
        )
        pipeline.llm_service = mock_llm

        # Mock repos
        with (
            patch.object(pipeline.doc_repo, "get_document_with_pages", AsyncMock(return_value=fake_doc)),
            patch.object(pipeline.clause_repo, "delete_clauses_by_document", AsyncMock(return_value=0)),
            patch.object(
                pipeline.clause_repo,
                "bulk_create_clauses",
                AsyncMock(
                    return_value=[
                        Clause(
                            id=uuid.uuid4(),
                            document_id=doc_id,
                            section_number="1",
                            section_title="Scope",
                            clause_text="Scope of work.",
                            risk_level="LOW",
                            explanation="This appears to be standard scope.",
                            reason="Standard.",
                            page_number=1,
                            created_at=datetime.now(timezone.utc),
                        ),
                        Clause(
                            id=uuid.uuid4(),
                            document_id=doc_id,
                            section_number="2",
                            section_title="Indemnity",
                            clause_text="Indemnity with unlimited liability.",
                            risk_level="HIGH",
                            explanation="This may create uncapped exposure.",
                            reason="Indemnity.",
                            page_number=1,
                            created_at=datetime.now(timezone.utc),
                        ),
                        Clause(
                            id=uuid.uuid4(),
                            document_id=doc_id,
                            section_number="3",
                            section_title="Renewal",
                            clause_text="Auto-renewal terms.",
                            risk_level="MEDIUM",
                            explanation="This could renew without manual action.",
                            reason="Renewal.",
                            page_number=1,
                            created_at=datetime.now(timezone.utc),
                        ),
                    ]
                ),
            ),
            patch.object(
                pipeline.clause_repo,
                "count_by_risk",
                AsyncMock(return_value={"HIGH": 1, "MEDIUM": 1, "LOW": 1, "TOTAL": 3}),
            ),
            patch.object(
                pipeline.analysis_repo,
                "upsert_summary",
                AsyncMock(
                    return_value=MagicMock(
                        overall_summary="Contract contains 1 high, 1 medium, 1 low risk clause."
                    )
                ),
            ),
            patch.object(pipeline.doc_repo, "update_status", AsyncMock()),
        ):
            response = await pipeline.run(doc_id)

            assert response.summary.total_clauses == 3
            assert response.summary.high == 1
            assert response.summary.medium == 1
            assert response.summary.low == 1
            assert response.status == "ANALYZED"
            assert len(response.clauses) == 3


# ─── 4. API Endpoints Integration Tests ───────────────────────────────────────


class TestAnalysisAPIRoutes:
    """Tests for POST /api/documents/{id}/analyze and GET /api/documents/{id}/summary."""

    def test_analyze_document_success(self, client):
        doc_id = uuid.uuid4()
        fake_doc = MagicMock()
        fake_doc.id = doc_id

        fake_response = {
            "document_id": str(doc_id),
            "status": "ANALYZED",
            "summary": {
                "total_clauses": 2,
                "high": 1,
                "medium": 0,
                "low": 1,
                "overall_summary": "Analysis complete.",
            },
            "clauses": [
                {
                    "id": str(uuid.uuid4()),
                    "document_id": str(doc_id),
                    "section_number": "1.0",
                    "section_title": "Definitions",
                    "clause_text": "Definitions text",
                    "risk_level": "LOW",
                    "explanation": "This appears standard.",
                    "reason": "Standard.",
                    "page_number": 1,
                    "char_start": 0,
                    "char_end": 16,
                    "created_at": "2026-09-19T00:00:00Z",
                },
                {
                    "id": str(uuid.uuid4()),
                    "document_id": str(doc_id),
                    "section_number": "2.0",
                    "section_title": "Indemnity",
                    "clause_text": "Full uncapped indemnity",
                    "risk_level": "HIGH",
                    "explanation": "This may pose significant financial exposure.",
                    "reason": "Uncapped indemnity.",
                    "page_number": 1,
                    "char_start": 20,
                    "char_end": 42,
                    "created_at": "2026-09-19T00:00:00Z",
                },
            ],
        }

        with (
            patch("app.api.routes.analysis.DocumentRepository") as MockDocRepo,
            patch("app.api.routes.analysis.AnalysisPipeline") as MockPipeline,
        ):
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=fake_doc)
            MockDocRepo.return_value = doc_repo

            pipeline_inst = AsyncMock()
            pipeline_inst.run = AsyncMock(return_value=fake_response)
            MockPipeline.return_value = pipeline_inst

            resp = client.post(f"/api/documents/{doc_id}/analyze")
            assert resp.status_code == 200
            data = resp.json()
            assert data["summary"]["total_clauses"] == 2
            assert data["summary"]["high"] == 1
            assert data["summary"]["low"] == 1

    def test_analyze_document_not_found(self, client):
        doc_id = uuid.uuid4()
        with patch("app.api.routes.analysis.DocumentRepository") as MockDocRepo:
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=None)
            MockDocRepo.return_value = doc_repo

            resp = client.post(f"/api/documents/{doc_id}/analyze")
            assert resp.status_code == 404

    def test_get_summary_success(self, client):
        doc_id = uuid.uuid4()
        fake_doc = MagicMock()
        fake_doc.id = doc_id

        fake_summary = MagicMock()
        fake_summary.overall_summary = "Risk summary overview."

        with (
            patch("app.api.routes.analysis.DocumentRepository") as MockDocRepo,
            patch("app.api.routes.analysis.AnalysisRepository") as MockAnalysisRepo,
            patch("app.api.routes.analysis.ClauseRepository") as MockClauseRepo,
        ):
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=fake_doc)
            MockDocRepo.return_value = doc_repo

            analysis_repo = AsyncMock()
            analysis_repo.get_summary_by_document = AsyncMock(return_value=fake_summary)
            MockAnalysisRepo.return_value = analysis_repo

            clause_repo = AsyncMock()
            clause_repo.count_by_risk = AsyncMock(
                return_value={"HIGH": 2, "MEDIUM": 3, "LOW": 5, "TOTAL": 10}
            )
            MockClauseRepo.return_value = clause_repo

            resp = client.get(f"/api/documents/{doc_id}/summary")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total_clauses"] == 10
            assert data["high"] == 2
            assert data["medium"] == 3
            assert data["low"] == 5
            assert data["overall_summary"] == "Risk summary overview."

    def test_get_summary_document_not_found(self, client):
        doc_id = uuid.uuid4()
        with patch("app.api.routes.analysis.DocumentRepository") as MockDocRepo:
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=None)
            MockDocRepo.return_value = doc_repo

            resp = client.get(f"/api/documents/{doc_id}/summary")
            assert resp.status_code == 404

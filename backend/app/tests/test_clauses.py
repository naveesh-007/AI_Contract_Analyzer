"""
Unit and integration tests for Clause APIs:
- GET /api/documents/{document_id}/clauses (risk filtering, text search, pagination)
- GET /api/documents/{document_id}/clauses/{clause_id} (single clause retrieval, 404s)
"""
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.clause import Clause


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _make_dummy_clause(
    doc_id: uuid.UUID,
    risk: str = "LOW",
    title: str = "Confidentiality",
    text: str = "Contractor shall maintain confidentiality.",
) -> Clause:
    return Clause(
        id=uuid.uuid4(),
        document_id=doc_id,
        section_number="3.1",
        section_title=title,
        clause_text=text,
        risk_level=risk,
        explanation="This appears to be standard protection.",
        reason="Customary NDA terms.",
        page_number=1,
        char_start=0,
        char_end=len(text),
        created_at=datetime.now(timezone.utc),
    )


class TestClauseAPIRoutes:
    """Tests for clause retrieval, filtering, search, and pagination endpoints."""

    def test_list_clauses_with_risk_filter(self, client):
        doc_id = uuid.uuid4()
        fake_doc = MagicMock()
        fake_doc.id = doc_id

        high_clause = _make_dummy_clause(doc_id, risk="HIGH", title="Indemnity", text="Full uncapped indemnity")

        with (
            patch("app.api.routes.analysis.DocumentRepository") as MockDocRepo,
            patch("app.api.routes.analysis.ClauseRepository") as MockClauseRepo,
        ):
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=fake_doc)
            MockDocRepo.return_value = doc_repo

            clause_repo = AsyncMock()
            clause_repo.get_clauses_by_document = AsyncMock(return_value=([high_clause], 1))
            MockClauseRepo.return_value = clause_repo

            resp = client.get(f"/api/documents/{doc_id}/clauses?risk_level=HIGH")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 1
            assert len(data["items"]) == 1
            assert data["items"][0]["risk_level"] == "HIGH"
            clause_repo.get_clauses_by_document.assert_called_once_with(
                document_id=doc_id,
                risk_level="HIGH",
                search=None,
                page=1,
                page_size=20,
            )

    def test_list_clauses_with_search_and_pagination(self, client):
        doc_id = uuid.uuid4()
        fake_doc = MagicMock()
        fake_doc.id = doc_id

        clause1 = _make_dummy_clause(doc_id, text="Termination for convenience")

        with (
            patch("app.api.routes.analysis.DocumentRepository") as MockDocRepo,
            patch("app.api.routes.analysis.ClauseRepository") as MockClauseRepo,
        ):
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=fake_doc)
            MockDocRepo.return_value = doc_repo

            clause_repo = AsyncMock()
            clause_repo.get_clauses_by_document = AsyncMock(return_value=([clause1], 25))
            MockClauseRepo.return_value = clause_repo

            resp = client.get(f"/api/documents/{doc_id}/clauses?search=terminate&page=2&page_size=10")
            assert resp.status_code == 200
            data = resp.json()
            assert data["total"] == 25
            assert data["page"] == 2
            assert data["page_size"] == 10
            assert data["total_pages"] == 3

    def test_get_single_clause_success(self, client):
        doc_id = uuid.uuid4()
        clause_id = uuid.uuid4()
        fake_doc = MagicMock()
        fake_doc.id = doc_id

        clause = _make_dummy_clause(doc_id)
        clause.id = clause_id

        with (
            patch("app.api.routes.analysis.DocumentRepository") as MockDocRepo,
            patch("app.api.routes.analysis.ClauseRepository") as MockClauseRepo,
        ):
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=fake_doc)
            MockDocRepo.return_value = doc_repo

            clause_repo = AsyncMock()
            clause_repo.get_clause = AsyncMock(return_value=clause)
            MockClauseRepo.return_value = clause_repo

            resp = client.get(f"/api/documents/{doc_id}/clauses/{clause_id}")
            assert resp.status_code == 200
            data = resp.json()
            assert data["id"] == str(clause_id)
            assert data["document_id"] == str(doc_id)
            assert data["section_title"] == "Confidentiality"

    def test_get_single_clause_not_found(self, client):
        doc_id = uuid.uuid4()
        clause_id = uuid.uuid4()
        fake_doc = MagicMock()
        fake_doc.id = doc_id

        with (
            patch("app.api.routes.analysis.DocumentRepository") as MockDocRepo,
            patch("app.api.routes.analysis.ClauseRepository") as MockClauseRepo,
        ):
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=fake_doc)
            MockDocRepo.return_value = doc_repo

            clause_repo = AsyncMock()
            clause_repo.get_clause = AsyncMock(return_value=None)
            MockClauseRepo.return_value = clause_repo

            resp = client.get(f"/api/documents/{doc_id}/clauses/{clause_id}")
            assert resp.status_code == 404

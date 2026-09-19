"""
Unit and integration tests for Document-Grounded AI Chat (RAG).

Tests:
TEST 1: Question answer exists in document.
TEST 2: Question answer does NOT exist.
TEST 3: Question attempts to force outside knowledge.
TEST 4: Chat source references correct clause.
TEST 5: Clicking source / scoping isolates document chunks.
TEST 6: Long document retrieval returns relevant chunks.
TEST 7: No retrieved evidence returns not found response.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models.chat import ChatMessage, ChatSession, ChatSource
from app.models.chunk import DocumentChunk
from app.models.clause import Clause
from app.models.document import Document, DocumentPage
from app.schemas.chat import ChatResponse
from app.services.embedding_service import MockEmbeddingProvider, cosine_similarity
from app.services.rag_service import NOT_FOUND_MESSAGE, RAGService


@pytest.fixture
def client():
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def create_session_mock():
    s = AsyncMock()
    s.add = MagicMock()
    s.add_all = MagicMock()
    s.flush = AsyncMock()
    return s


# ─── 1. Vector Math & Embedding Unit Tests ────────────────────────────────────


class TestEmbeddingAndVectorMath:
    """Tests for vector math and deterministic embeddings."""

    @pytest.mark.asyncio
    async def test_cosine_similarity_identical_vectors(self):
        v = [1.0, 0.0, 0.0]
        assert cosine_similarity(v, v) == 1.0

    @pytest.mark.asyncio
    async def test_cosine_similarity_orthogonal_vectors(self):
        v1 = [1.0, 0.0]
        v2 = [0.0, 1.0]
        assert cosine_similarity(v1, v2) == 0.0

    @pytest.mark.asyncio
    async def test_mock_embedding_provider_relevance(self):
        provider = MockEmbeddingProvider()
        e_term = await provider.get_embedding("termination of lease agreement")
        e_cancel = await provider.get_embedding("terminate and cancel agreement")
        e_unrelated = await provider.get_embedding("astrophysics quantum mechanics galaxy")

        sim_related = cosine_similarity(e_term, e_cancel)
        sim_unrelated = cosine_similarity(e_term, e_unrelated)

        assert sim_related > sim_unrelated
        assert sim_related > 0.4


# ─── 2. Grounding & RAG Pipeline Tests ────────────────────────────────────────


class TestRAGPipeline:
    """Tests for document-grounded answer generation and scoping."""

    @pytest.mark.asyncio
    async def test_grounded_answer_when_information_exists(self):
        """TEST 1 & TEST 4: Question answer exists in document and source references correct clause."""
        session = create_session_mock()
        rag = RAGService(session)
        doc_id = uuid.uuid4()
        clause_id = uuid.uuid4()

        fake_clause = Clause(
            id=clause_id,
            document_id=doc_id,
            section_number="8.2",
            section_title="Termination",
            clause_text="Either party may terminate this agreement with 30 days prior written notice.",
            risk_level="LOW",
            explanation="Standard 30 days notice required.",
            reason="Customary.",
            page_number=2,
        )

        chunk_text = "Section 8.2 Termination:\nEither party may terminate this agreement with 30 days prior written notice."
        embed = await MockEmbeddingProvider().get_embedding(chunk_text)

        fake_chunk = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            clause_id=clause_id,
            page_number=2,
            chunk_text=chunk_text,
            embedding=embed,
        )
        fake_chunk.clause = fake_clause

        with (
            patch.object(rag, "ensure_document_chunks", AsyncMock(return_value=[fake_chunk])),
            patch.object(
                rag,
                "get_or_create_session",
                AsyncMock(return_value=ChatSession(id=uuid.uuid4(), document_id=doc_id)),
            ),
        ):
            resp = await rag.answer_question(
                document_id=doc_id,
                question="Can I terminate this agreement early?",
            )

            assert resp.grounded is True
            assert NOT_FOUND_MESSAGE not in resp.answer
            assert len(resp.sources) > 0
            assert resp.sources[0].clause_id == clause_id
            assert resp.sources[0].page_number == 2

    @pytest.mark.asyncio
    async def test_unanswered_question_returns_not_found(self):
        """TEST 2: When answer does NOT exist in document, returns clear not-found message."""
        session = create_session_mock()
        rag = RAGService(session)
        doc_id = uuid.uuid4()

        fake_chunk = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            page_number=1,
            chunk_text="Section 1.0 Definitions: The definitions set forth herein shall govern.",
            embedding=[0.01] * 128,
        )
        fake_chunk.clause = None

        with (
            patch.object(rag, "ensure_document_chunks", AsyncMock(return_value=[fake_chunk])),
            patch.object(
                rag,
                "get_or_create_session",
                AsyncMock(return_value=ChatSession(id=uuid.uuid4(), document_id=doc_id)),
            ),
        ):
            resp = await rag.answer_question(
                document_id=doc_id,
                question="What is the monthly parking fee for the motorcycle garage?",
            )

            assert resp.grounded is False
            assert resp.answer == NOT_FOUND_MESSAGE
            assert len(resp.sources) == 0

    @pytest.mark.asyncio
    async def test_outside_legal_knowledge_is_blocked(self):
        """TEST 3: Question attempting to force external legal statutes is rejected."""
        session = create_session_mock()
        rag = RAGService(session)
        doc_id = uuid.uuid4()

        fake_chunk = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_id,
            page_number=1,
            chunk_text="Rental Agreement for Flat 4B Maple St.",
            embedding=[0.1] * 128,
        )
        fake_chunk.clause = None

        with (
            patch.object(rag, "ensure_document_chunks", AsyncMock(return_value=[fake_chunk])),
            patch.object(
                rag,
                "get_or_create_session",
                AsyncMock(return_value=ChatSession(id=uuid.uuid4(), document_id=doc_id)),
            ),
        ):
            resp = await rag.answer_question(
                document_id=doc_id,
                question="What does Indian tenancy law say about this?",
            )

            assert resp.grounded is False
            assert resp.answer == NOT_FOUND_MESSAGE
            assert len(resp.sources) == 0

    @pytest.mark.asyncio
    async def test_document_scoping_isolation(self):
        """TEST 5: Retrieval is strictly isolated by document_id."""
        session = create_session_mock()
        rag = RAGService(session)
        doc_a = uuid.uuid4()
        doc_b = uuid.uuid4()

        chunk_a = DocumentChunk(
            id=uuid.uuid4(),
            document_id=doc_a,
            page_number=1,
            chunk_text="Contract A secret clause text",
            embedding=[0.9] * 128,
        )

        with patch.object(rag, "ensure_document_chunks", AsyncMock(return_value=[chunk_a])) as mock_ensure:
            await rag.retrieve_relevant_chunks(document_id=doc_a, question="test")
            mock_ensure.assert_called_once_with(doc_a)

    @pytest.mark.asyncio
    async def test_long_document_retrieval_returns_relevant_chunks(self):
        """TEST 6: Long document retrieval returns the most relevant chunks across multiple pages."""
        session = create_session_mock()
        rag = RAGService(session)
        doc_id = uuid.uuid4()
        provider = MockEmbeddingProvider()

        chunks = []
        # Create 15 chunks across 15 pages
        for page in range(1, 16):
            if page == 12:
                text = "Section 12.4 Maintenance: Tenant is responsible for all HVAC maintenance costs exceeding $500."
            else:
                text = f"Section {page}.0 Miscellaneous provision number {page} regarding general terms."

            embed = await provider.get_embedding(text)
            c = DocumentChunk(
                id=uuid.uuid4(),
                document_id=doc_id,
                page_number=page,
                chunk_text=text,
                embedding=embed,
            )
            c.clause = None
            chunks.append(c)

        with patch.object(rag, "ensure_document_chunks", AsyncMock(return_value=chunks)):
            top = await rag.retrieve_relevant_chunks(
                document_id=doc_id,
                question="Who is responsible for HVAC maintenance?",
                top_k=3,
            )
            assert len(top) > 0
            best_chunk, best_score = top[0]
            assert best_chunk.page_number == 12
            assert "HVAC maintenance" in best_chunk.chunk_text

    @pytest.mark.asyncio
    async def test_no_retrieved_evidence_returns_not_found(self):
        """TEST 7: No retrieved evidence returns 'I couldn't find this information in the uploaded document.'"""
        session = create_session_mock()
        rag = RAGService(session)
        doc_id = uuid.uuid4()

        with (
            patch.object(rag, "ensure_document_chunks", AsyncMock(return_value=[])),
            patch.object(
                rag,
                "get_or_create_session",
                AsyncMock(return_value=ChatSession(id=uuid.uuid4(), document_id=doc_id)),
            ),
        ):
            resp = await rag.answer_question(
                document_id=doc_id,
                question="What is the interest rate on overdue invoices?",
            )

            assert resp.grounded is False
            assert resp.answer == NOT_FOUND_MESSAGE
            assert len(resp.sources) == 0


# ─── 3. Chat API Endpoint Integration Tests ───────────────────────────────────


class TestChatAPIRoutes:
    """Tests for POST /api/documents/{id}/chat and GET /api/documents/{id}/chat/history."""

    def test_chat_endpoint_success(self, client):
        doc_id = uuid.uuid4()
        session_id = uuid.uuid4()
        msg_id = uuid.uuid4()

        fake_doc = MagicMock()
        fake_doc.id = doc_id

        fake_chat_response = ChatResponse(
            answer="According to Section 3.1, payment is due on the first of each month.",
            grounded=True,
            sources=[
                {
                    "clause_id": str(uuid.uuid4()),
                    "section": "Section 3.1",
                    "page_number": 1,
                    "relevance_score": 0.92,
                }
            ],
            session_id=session_id,
            message_id=msg_id,
        )

        with (
            patch("app.api.routes.chat.DocumentRepository") as MockDocRepo,
            patch("app.api.routes.chat.RAGService") as MockRAG,
        ):
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=fake_doc)
            MockDocRepo.return_value = doc_repo

            rag_inst = AsyncMock()
            rag_inst.answer_question = AsyncMock(return_value=fake_chat_response)
            MockRAG.return_value = rag_inst

            resp = client.post(
                f"/api/documents/{doc_id}/chat",
                json={"question": "When is payment due?", "session_id": str(session_id)},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["grounded"] is True
            assert "payment is due" in data["answer"].lower()
            assert len(data["sources"]) == 1
            assert data["sources"][0]["section"] == "Section 3.1"

    def test_chat_endpoint_document_not_found(self, client):
        doc_id = uuid.uuid4()
        with patch("app.api.routes.chat.DocumentRepository") as MockDocRepo:
            doc_repo = AsyncMock()
            doc_repo.get_document = AsyncMock(return_value=None)
            MockDocRepo.return_value = doc_repo

            resp = client.post(
                f"/api/documents/{doc_id}/chat",
                json={"question": "What is the penalty?"},
            )
            assert resp.status_code == 404


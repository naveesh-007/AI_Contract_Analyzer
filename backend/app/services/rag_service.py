"""
Document-Grounded RAG Service for Contract Q&A.

Implements strict document-grounded question answering:
1. Question Embedding
2. Scoped Vector Retrieval (document_id isolated)
3. Strict Grounding LLM Prompting
4. Persistence of Sessions, Messages, and Source Citations
"""
import json
import logging
import re
import uuid
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage, ChatSession, ChatSource
from app.models.chunk import DocumentChunk
from app.models.clause import Clause
from app.models.document import Document
from app.schemas.chat import ChatResponse, ChatSourceOut
from app.services.chunking_service import ChunkingService
from app.services.embedding_service import EmbeddingService, cosine_similarity
from app.services.llm_service import BaseLLMProvider, LLMService, extract_json_from_text

logger = logging.getLogger(__name__)

NOT_FOUND_MESSAGE = "I couldn't find this information in the uploaded document."

RAG_SYSTEM_PROMPT = """You are a document-grounded assistant for legal contracts.
You may only answer using the supplied document evidence.
Do not use general legal knowledge.
Do not invent facts.
Do not guess.
Do not invent clauses.
Do not invent page numbers.
Do not invent section numbers.

If the supplied evidence does not contain enough information to answer the question, say:
'I couldn't find this information in the uploaded document.'

You MUST format your output strictly as a JSON object:
{
  "answer": "Clear, direct, factual answer based ONLY on the provided document excerpts, or 'I couldn't find this information in the uploaded document.'",
  "grounded": true,
  "sources": [
    {
      "clause_id": "UUID from evidence or null",
      "section": "Section number or title from evidence or null",
      "page_number": 1
    }
  ]
}

If the question cannot be answered from the provided excerpts or asks about external laws/parties not in the document, set "grounded": false, "sources": [], and "answer": "I couldn't find this information in the uploaded document."
"""


class RAGService:
    """Coordinates vector retrieval, grounded prompt construction, and conversation persistence."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_service: Optional[EmbeddingService] = None,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        self.session = session
        self.embedding_service = embedding_service or EmbeddingService()
        self.llm_service = llm_service or LLMService()

    async def get_or_create_session(
        self, document_id: uuid.UUID, session_id: Optional[uuid.UUID] = None
    ) -> ChatSession:
        """Retrieves an existing chat session or creates a new one for the document."""
        if session_id:
            result = await self.session.execute(
                select(ChatSession).where(
                    ChatSession.id == session_id,
                    ChatSession.document_id == document_id,
                )
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing

        # Create new session
        new_session = ChatSession(document_id=document_id)
        self.session.add(new_session)
        await self.session.flush()
        return new_session

    async def ensure_document_chunks(self, document_id: uuid.UUID) -> list[DocumentChunk]:
        """Ensures document chunks and embeddings exist for vector search."""
        result = await self.session.execute(
            select(DocumentChunk)
            .options(selectinload(DocumentChunk.clause))
            .where(DocumentChunk.document_id == document_id)
        )
        chunks = list(result.scalars().all())
        if chunks:
            return chunks

        # Generate chunks on-demand from document pages & clauses
        doc_result = await self.session.execute(
            select(Document)
            .options(selectinload(Document.pages), selectinload(Document.clauses))
            .where(Document.id == document_id)
        )
        doc = doc_result.scalar_one_or_none()
        if not doc or not doc.pages:
            return []

        chunker = ChunkingService(self.session, self.embedding_service)
        return await chunker.create_chunks_for_document(
            document_id=document_id,
            pages=doc.pages,
            clauses=doc.clauses or [],
        )

    async def retrieve_relevant_chunks(
        self,
        document_id: uuid.UUID,
        question: str,
        top_k: int = 4,
    ) -> list[tuple[DocumentChunk, float]]:
        """
        Retrieves top-k relevant document chunks for the question.
        STRICT SECURITY: Isolated strictly by document_id.
        """
        chunks = await self.ensure_document_chunks(document_id)
        if not chunks:
            return []

        # Generate query embedding
        try:
            query_vec = await self.embedding_service.get_embedding(question)
        except Exception as exc:
            logger.warning("Query embedding generation failed: %s", exc)
            query_vec = []

        scored_chunks: list[tuple[DocumentChunk, float]] = []

        for chunk in chunks:
            if chunk.embedding and query_vec:
                score = cosine_similarity(query_vec, chunk.embedding)
            else:
                # Text overlap keyword fallback
                q_words = set(re.findall(r"\w+", question.lower()))
                c_words = set(re.findall(r"\w+", chunk.chunk_text.lower()))
                overlap = len(q_words & c_words)
                score = overlap / max(len(q_words), 1)

            scored_chunks.append((chunk, score))

        # Sort descending by relevance score
        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        return scored_chunks[:top_k]

    async def answer_question(
        self,
        document_id: uuid.UUID,
        question: str,
        session_id: Optional[uuid.UUID] = None,
    ) -> ChatResponse:
        """
        End-to-end RAG question answering pipeline with strict grounding.
        """
        chat_session = await self.get_or_create_session(document_id, session_id)

        # 1. Retrieve relevant evidence chunks
        top_scored_chunks = await self.retrieve_relevant_chunks(document_id, question, top_k=4)

        # 2. Check if any evidence found
        if not top_scored_chunks or all(score < 0.05 for _, score in top_scored_chunks):
            # No relevant document evidence found
            asst_id = uuid.uuid4()
            user_msg = ChatMessage(
                id=uuid.uuid4(),
                session_id=chat_session.id,
                role="user",
                message=question,
                grounded=True,
            )
            asst_msg = ChatMessage(
                id=asst_id,
                session_id=chat_session.id,
                role="assistant",
                message=NOT_FOUND_MESSAGE,
                grounded=False,
            )
            self.session.add_all([user_msg, asst_msg])
            await self.session.flush()

            return ChatResponse(
                answer=NOT_FOUND_MESSAGE,
                grounded=False,
                sources=[],
                session_id=chat_session.id,
                message_id=asst_id,
            )

        # 3. Format evidence for the LLM
        evidence_snippets = []
        clause_map: dict[str, Any] = {}

        for i, (chunk, score) in enumerate(top_scored_chunks, start=1):
            c_id = str(chunk.clause_id) if chunk.clause_id else f"chunk-{i}"
            sec_name = f"Section {chunk.clause.section_number}" if chunk.clause and chunk.clause.section_number else (chunk.clause.section_title if chunk.clause else f"Excerpt {i}")
            p_num = chunk.page_number or 1

            clause_map[c_id] = {
                "clause_id": chunk.clause_id,
                "section": sec_name,
                "page_number": p_num,
                "score": round(score, 3),
            }

            evidence_snippets.append(
                f"[EVIDENCE {i}]\n"
                f"ID: {c_id}\n"
                f"Section: {sec_name}\n"
                f"Page: {p_num}\n"
                f"Text: {chunk.chunk_text}\n"
            )

        context_prompt = (
            f"USER QUESTION: {question}\n\n"
            f"DOCUMENT EVIDENCE EXCERPTS:\n"
            f"{'---'.join(evidence_snippets)}\n\n"
            f"Answer the user question strictly using only the above excerpts in required JSON format."
        )

        # 4. Generate grounded answer via LLM (with graceful heuristic fallback)
        try:
            raw_response = await self.llm_service.provider.generate_raw(
                context_prompt, system_prompt=RAG_SYSTEM_PROMPT
            )
        except Exception as llm_exc:
            logger.warning("RAG external LLM failed (%s), falling back to mock heuristic provider.", llm_exc)
            from app.services.llm_service import MockLLMProvider
            raw_response = await MockLLMProvider().generate_raw(
                context_prompt, system_prompt=RAG_SYSTEM_PROMPT
            )

        try:
            parsed = extract_json_from_text(raw_response)
            answer_text = parsed.get("answer", NOT_FOUND_MESSAGE)
            is_grounded = bool(parsed.get("grounded", True))
            raw_sources = parsed.get("sources", [])
        except Exception:
            # Fallback if raw text returned
            answer_text = raw_response.strip()
            is_grounded = NOT_FOUND_MESSAGE.lower() not in answer_text.lower()
            raw_sources = []

        # If answer says not found or outside scope, force grounded=False
        if NOT_FOUND_MESSAGE.lower() in answer_text.lower():
            is_grounded = False
            raw_sources = []

        # 5. Build structured source citations
        sources_out: list[ChatSourceOut] = []
        db_sources: list[ChatSource] = []

        if is_grounded:
            if raw_sources:
                for s in raw_sources:
                    c_id_raw = s.get("clause_id")
                    matched_info = clause_map.get(str(c_id_raw)) if c_id_raw else None
                    cid_uuid = None
                    if matched_info and matched_info["clause_id"]:
                        cid_uuid = matched_info["clause_id"]
                    elif c_id_raw:
                        try:
                            cid_uuid = uuid.UUID(str(c_id_raw))
                        except Exception:
                            cid_uuid = None

                    sec = s.get("section") or (matched_info["section"] if matched_info else None)
                    p_num = s.get("page_number") or (matched_info["page_number"] if matched_info else 1)
                    score = matched_info["score"] if matched_info else 0.85

                    sources_out.append(
                        ChatSourceOut(
                            clause_id=cid_uuid,
                            section=sec,
                            page_number=p_num,
                            relevance_score=score,
                        )
                    )
            else:
                # Use top retrieved chunk as primary source citation
                top_chunk, top_score = top_scored_chunks[0]
                sec_name = f"Section {top_chunk.clause.section_number}" if top_chunk.clause and top_chunk.clause.section_number else (top_chunk.clause.section_title if top_chunk.clause else "General Provision")
                sources_out.append(
                    ChatSourceOut(
                        clause_id=top_chunk.clause_id,
                        section=sec_name,
                        page_number=top_chunk.page_number or 1,
                        relevance_score=round(top_score, 3),
                    )
                )

        # 6. Persist user and assistant messages
        user_msg_id = uuid.uuid4()
        asst_msg_id = uuid.uuid4()

        user_msg = ChatMessage(
            id=user_msg_id,
            session_id=chat_session.id,
            role="user",
            message=question,
            grounded=True,
        )
        asst_msg = ChatMessage(
            id=asst_msg_id,
            session_id=chat_session.id,
            role="assistant",
            message=answer_text,
            grounded=is_grounded,
        )
        self.session.add_all([user_msg, asst_msg])
        await self.session.flush()

        # Persist sources
        for s in sources_out:
            db_source = ChatSource(
                id=uuid.uuid4(),
                message_id=asst_msg_id,
                clause_id=s.clause_id,
                page_number=s.page_number,
                relevance_score=s.relevance_score,
            )
            self.session.add(db_source)
        await self.session.flush()

        return ChatResponse(
            answer=answer_text,
            grounded=is_grounded,
            sources=sources_out,
            session_id=chat_session.id,
            message_id=asst_msg_id,
        )

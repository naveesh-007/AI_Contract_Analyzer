"""
Chat API routes for Document-Grounded Legal Q&A.

POST /api/documents/{document_id}/chat          — Ask a question with strict document grounding
GET  /api/documents/{document_id}/chat/history  — Retrieve chat history and citations for a session
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.chat import ChatMessage, ChatSession, ChatSource
from app.models.clause import Clause
from app.repositories.document_repo import DocumentRepository
from app.schemas.chat import (
    ChatHistoryResponse,
    ChatMessageOut,
    ChatRequest,
    ChatResponse,
    ChatSourceOut,
)
from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Document Chat"])


@router.post(
    "/{document_id}/chat",
    response_model=ChatResponse,
    status_code=status.HTTP_200_OK,
    summary="Ask a grounded question about an uploaded document",
)
async def chat_with_document(
    document_id: uuid.UUID,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
) -> ChatResponse:
    """
    Submits a question to the document-grounded RAG pipeline:
    1. Vector retrieval finds the most relevant document chunks
    2. Strict grounding instructions require the LLM to answer using ONLY the document
    3. Returns the answer, grounded status, and source citations
    4. Persists the conversation thread
    """
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    rag = RAGService(db)
    try:
        response = await rag.answer_question(
            document_id=document_id,
            question=payload.question,
            session_id=payload.session_id,
        )
        return response
    except Exception as exc:
        logger.exception("Error processing chat for document %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate grounded answer: {exc}",
        )


@router.get(
    "/{document_id}/chat/history",
    response_model=ChatHistoryResponse,
    summary="Retrieve chat message history and source citations for a document session",
)
async def get_chat_history(
    document_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = Query(
        default=None,
        description="Session ID (if omitted, the most recent session is returned)",
    ),
    db: AsyncSession = Depends(get_db),
) -> ChatHistoryResponse:
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    # Find requested session or most recent session for this document
    query = (
        select(ChatSession)
        .options(
            selectinload(ChatSession.messages).selectinload(ChatMessage.sources).selectinload(ChatSource.clause)
        )
        .where(ChatSession.document_id == document_id)
    )

    if session_id:
        query = query.where(ChatSession.id == session_id)
    else:
        query = query.order_by(ChatSession.created_at.desc())

    result = await db.execute(query)
    chat_session = result.scalars().first()

    if not chat_session:
        # Create a fresh empty session
        chat_session = ChatSession(document_id=document_id)
        db.add(chat_session)
        await db.flush()
        return ChatHistoryResponse(
            session_id=chat_session.id,
            document_id=document_id,
            messages=[],
        )

    messages_out: list[ChatMessageOut] = []
    for msg in chat_session.messages:
        sources_out: list[ChatSourceOut] = []
        for src in msg.sources:
            sec_title = None
            if src.clause:
                sec_title = f"Section {src.clause.section_number}" if src.clause.section_number else src.clause.section_title
            sources_out.append(
                ChatSourceOut(
                    clause_id=src.clause_id,
                    section=sec_title or "General Provision",
                    page_number=src.page_number or 1,
                    relevance_score=src.relevance_score,
                )
            )

        messages_out.append(
            ChatMessageOut(
                id=msg.id,
                session_id=msg.session_id,
                role=msg.role,  # type: ignore[arg-type]
                message=msg.message,
                grounded=msg.grounded,
                sources=sources_out,
                created_at=msg.created_at,
            )
        )

    return ChatHistoryResponse(
        session_id=chat_session.id,
        document_id=document_id,
        messages=messages_out,
    )

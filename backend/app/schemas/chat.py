"""
Pydantic schemas for Document-Grounded RAG Chat.
"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatSourceOut(BaseModel):
    """Citation source linking an answer to a contract clause and page."""

    model_config = ConfigDict(from_attributes=True)

    clause_id: Optional[uuid.UUID] = None
    section: Optional[str] = None
    page_number: Optional[int] = None
    relevance_score: Optional[float] = None
    snippet: Optional[str] = None


class ChatRequest(BaseModel):
    """Input payload for POST /api/documents/{document_id}/chat."""

    question: str = Field(..., min_length=1, max_length=2000, description="User question about the document")
    session_id: Optional[uuid.UUID] = Field(default=None, description="Optional chat session ID to continue a thread")


class ChatResponse(BaseModel):
    """Strictly grounded response returned by the chat API."""

    answer: str = Field(..., description="Document-grounded answer or not-found explanation")
    grounded: bool = Field(..., description="True if answer is backed by document evidence, False if question is out of scope")
    sources: list[ChatSourceOut] = Field(default_factory=list, description="Citations to document clauses and pages")
    session_id: uuid.UUID
    message_id: uuid.UUID


class ChatMessageOut(BaseModel):
    """Individual message in chat history."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: Literal["user", "assistant", "system"]
    message: str
    grounded: bool = True
    sources: list[ChatSourceOut] = Field(default_factory=list)
    created_at: datetime


class ChatHistoryResponse(BaseModel):
    """Chat history for a document session."""

    session_id: uuid.UUID
    document_id: uuid.UUID
    messages: list[ChatMessageOut]

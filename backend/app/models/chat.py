"""
SQLAlchemy ORM models for chat_sessions, chat_messages, and chat_sources.
"""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.clause import Clause
    from app.models.document import Document


def _now() -> datetime:
    return datetime.now(timezone.utc)


class ChatSession(Base):
    """Represents a conversational chat session scoped per document."""

    __tablename__ = "chat_sessions"
    __table_args__ = (
        Index("ix_chat_sessions_document_id", "document_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    document: Mapped["Document"] = relationship("Document")
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        order_by="ChatMessage.created_at",
    )


class ChatMessage(Base):
    """Represents a single message in a chat session with grounding verification."""

    __tablename__ = "chat_messages"
    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'system')",
            name="chk_chat_message_role",
        ),
        Index("ix_chat_messages_session_id", "session_id"),
        Index("ix_chat_messages_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # user | assistant | system
    message: Mapped[str] = mapped_column(Text, nullable=False)
    grounded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")
    sources: Mapped[list["ChatSource"]] = relationship(
        "ChatSource",
        back_populates="message",
        cascade="all, delete-orphan",
    )


class ChatSource(Base):
    """Stores citation sources linking an assistant message to document clauses and pages."""

    __tablename__ = "chat_sources"
    __table_args__ = (
        Index("ix_chat_sources_message_id", "message_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    message_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_messages.id", ondelete="CASCADE"),
        nullable=False,
    )
    clause_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clauses.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    relevance_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    message: Mapped["ChatMessage"] = relationship("ChatMessage", back_populates="sources")
    clause: Mapped[Optional["Clause"]] = relationship("Clause")

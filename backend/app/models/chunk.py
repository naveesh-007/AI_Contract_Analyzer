"""
SQLAlchemy ORM model for document_chunks.
"""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    JSON,
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


class DocumentChunk(Base):
    """
    Stores an individual text chunk with vector embeddings for RAG similarity search.
    """

    __tablename__ = "document_chunks"
    __table_args__ = (
        Index("ix_document_chunks_document_id", "document_id"),
        Index("ix_document_chunks_clause_id", "clause_id"),
        Index("ix_document_chunks_page_number", "page_number"),
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
    clause_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clauses.id", ondelete="SET NULL"),
        nullable=True,
    )
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    chunk_text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    embedding: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    document: Mapped["Document"] = relationship("Document")
    clause: Mapped[Optional["Clause"]] = relationship("Clause")

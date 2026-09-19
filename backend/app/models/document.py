"""
SQLAlchemy ORM models for documents and document_pages.
"""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum,
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
    from app.models.analysis_summary import AnalysisSummary
    from app.models.clause import Clause


class DocumentStatus(str):
    """Document processing status values."""
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    ANALYZED = "ANALYZED"
    FAILED = "FAILED"


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Document(Base):
    """
    Represents an uploaded legal document.

    Columns:
        id            UUID primary key
        filename      original uploaded filename (sanitized)
        document_type user-selected type (Rental Agreement, etc.)
        file_type     pdf | txt
        file_size     bytes
        status        UPLOADED | PROCESSING | ANALYZED | FAILED
        created_at    UTC timestamp
        updated_at    UTC timestamp (auto-updated)
    """

    __tablename__ = "documents"
    __table_args__ = (
        Index("ix_documents_status", "status"),
        Index("ix_documents_created_at", "created_at"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    document_type: Mapped[str] = mapped_column(String(100), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | txt
    file_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum(
            "UPLOADED", "PROCESSING", "ANALYZED", "FAILED",
            name="document_status",
            create_type=True,
        ),
        nullable=False,
        default="UPLOADED",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    # Relationship to pages
    pages: Mapped[list["DocumentPage"]] = relationship(
        "DocumentPage",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentPage.page_number",
    )

    # Relationship to clauses
    clauses: Mapped[list["Clause"]] = relationship(
        "Clause",
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="Clause.created_at",
    )

    # Relationship to analysis summary (one-to-one)
    analysis_summary: Mapped["AnalysisSummary | None"] = relationship(
        "AnalysisSummary",
        back_populates="document",
        cascade="all, delete-orphan",
        uselist=False,
    )


class DocumentPage(Base):
    """
    Stores text extracted from a single page of a document.

    Columns:
        id            UUID primary key
        document_id   FK → documents.id
        page_number   1-indexed page number
        text          extracted text content
        char_start    character offset start in the full document text
        char_end      character offset end in the full document text
    """

    __tablename__ = "document_pages"
    __table_args__ = (
        Index("ix_document_pages_document_id", "document_id"),
        Index("ix_document_pages_page_number", "page_number"),
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
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    char_start: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    char_end: Mapped[int | None] = mapped_column(BigInteger, nullable=True)

    document: Mapped["Document"] = relationship("Document", back_populates="pages")

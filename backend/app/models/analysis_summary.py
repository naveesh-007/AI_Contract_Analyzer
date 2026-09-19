"""
SQLAlchemy ORM model for analysis_summaries.
"""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.document import Document


def _now() -> datetime:
    return datetime.now(timezone.utc)


class AnalysisSummary(Base):
    """
    Stores aggregated risk counts and overall summary for a document.

    Columns:
        id              UUID primary key
        document_id     FK → documents.id (unique per document)
        total_clauses   total count of extracted clauses
        high_count      count of HIGH risk clauses
        medium_count    count of MEDIUM risk clauses
        low_count       count of LOW risk clauses
        overall_summary overall plain-language assessment of the contract
        created_at      UTC timestamp
    """

    __tablename__ = "analysis_summaries"
    __table_args__ = (
        UniqueConstraint("document_id", name="uq_analysis_summaries_document_id"),
        Index("ix_analysis_summaries_document_id", "document_id"),
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
    total_clauses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    high_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    medium_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    low_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    overall_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    document: Mapped["Document"] = relationship("Document", back_populates="analysis_summary")

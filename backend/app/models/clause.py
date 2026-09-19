"""
SQLAlchemy ORM model for clauses.
"""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
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
    from app.models.document import Document


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Clause(Base):
    """
    Stores an individual analyzed contractual clause.

    Columns:
        id              UUID primary key
        document_id     FK → documents.id
        section_number  e.g. '8.2', 'Section 3', 'IV' (nullable)
        section_title   e.g. 'Termination', 'Indemnification' (nullable)
        clause_text     exact verbatim text of the clause
        risk_level      LOW | MEDIUM | HIGH
        explanation     plain-language explanation for non-lawyers
        reason          risk rationale / flags
        page_number     1-indexed page number where clause starts (nullable)
        char_start      character start offset in document text
        char_end        character end offset in document text
        created_at      UTC timestamp
    """

    __tablename__ = "clauses"
    __table_args__ = (
        CheckConstraint(
            "risk_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="chk_clause_risk_level",
        ),
        Index("ix_clauses_document_id", "document_id"),
        Index("ix_clauses_risk_level", "risk_level"),
        Index("ix_clauses_page_number", "page_number"),
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
    section_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    clause_text: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), nullable=False)  # LOW, MEDIUM, HIGH
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    char_start: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    char_end: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    document: Mapped["Document"] = relationship("Document", back_populates="clauses")

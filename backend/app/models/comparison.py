"""
SQLAlchemy ORM models for standard contract templates, standard benchmark clauses,
and clause comparisons (SRS-S02 Standard Clause Comparison).
"""
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
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


class StandardContractTemplate(Base):
    """
    Stores archetypal standard benchmark templates (e.g., Rental Agreement, Freelance Contract).
    """

    __tablename__ = "standard_contract_templates"
    __table_args__ = (
        Index("ix_standard_templates_document_type", "document_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    document_type: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    version: Mapped[str] = mapped_column(String(20), nullable=False, default="1.0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now, onupdate=_now
    )

    clauses: Mapped[list["StandardClause"]] = relationship(
        "StandardClause",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="StandardClause.created_at",
    )


class StandardClause(Base):
    """
    Stores individual benchmark standard clauses for a template category.
    """

    __tablename__ = "standard_clauses"
    __table_args__ = (
        Index("ix_standard_clauses_template_id", "template_id"),
        Index("ix_standard_clauses_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("standard_contract_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    benchmark_text: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    template: Mapped["StandardContractTemplate"] = relationship(
        "StandardContractTemplate", back_populates="clauses"
    )


class ClauseComparison(Base):
    """
    Stores comparison evaluation between an extracted clause and a standard benchmark clause.
    """

    __tablename__ = "clause_comparisons"
    __table_args__ = (
        CheckConstraint(
            "deviation_level IN ('LOW', 'MEDIUM', 'HIGH')",
            name="chk_clause_comparison_deviation_level",
        ),
        Index("ix_clause_comparisons_document_id", "document_id"),
        Index("ix_clause_comparisons_clause_id", "clause_id"),
        Index("ix_clause_comparisons_standard_id", "standard_clause_id"),
        Index("ix_clause_comparisons_deviation_level", "deviation_level"),
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
    clause_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("clauses.id", ondelete="CASCADE"),
        nullable=False,
    )
    standard_clause_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("standard_clauses.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    deviation_level: Mapped[str] = mapped_column(String(10), nullable=False)  # LOW, MEDIUM, HIGH
    similarity_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    comparison_summary: Mapped[str] = mapped_column(Text, nullable=False, default="")
    differences: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    document: Mapped["Document"] = relationship("Document")
    clause: Mapped["Clause"] = relationship("Clause")
    standard_clause: Mapped[Optional["StandardClause"]] = relationship("StandardClause")

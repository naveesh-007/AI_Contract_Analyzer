"""
Clause repository — database CRUD and search operations for contractual clauses.
"""
import uuid
from typing import Optional

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clause import Clause


class ClauseRepository:
    """Encapsulates DB operations for the Clause model."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_create_clauses(
        self,
        document_id: uuid.UUID,
        clause_data_list: list[dict],
    ) -> list[Clause]:
        """Insert multiple analyzed clauses for a document."""
        clauses = [
            Clause(
                document_id=document_id,
                section_number=c.get("section_number"),
                section_title=c.get("section_title"),
                clause_text=c["clause_text"],
                risk_level=c["risk_level"],
                explanation=c["explanation"],
                reason=c["reason"],
                page_number=c.get("page_number"),
                char_start=c.get("char_start"),
                char_end=c.get("char_end"),
            )
            for c in clause_data_list
        ]
        self.session.add_all(clauses)
        await self.session.flush()
        return clauses

    async def get_clause(self, clause_id: uuid.UUID) -> Clause | None:
        """Fetch a single clause by its primary key ID."""
        result = await self.session.execute(
            select(Clause).where(Clause.id == clause_id)
        )
        return result.scalar_one_or_none()

    async def get_clauses_by_document(
        self,
        document_id: uuid.UUID,
        risk_level: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Clause], int]:
        """
        Fetch clauses for a document with optional risk filtering, search, and pagination.
        Returns (items, total_count).
        """
        query = select(Clause).where(Clause.document_id == document_id)

        if risk_level:
            query = query.where(Clause.risk_level == risk_level.upper())

        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Clause.clause_text.ilike(search_pattern),
                    Clause.section_title.ilike(search_pattern),
                    Clause.explanation.ilike(search_pattern),
                    Clause.reason.ilike(search_pattern),
                )
            )

        # Count total matching rows
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar_one()

        # Apply ordering and pagination
        offset = (page - 1) * page_size
        paginated_query = (
            query.order_by(Clause.page_number.nulls_last(), Clause.created_at)
            .offset(offset)
            .limit(page_size)
        )
        result = await self.session.execute(paginated_query)
        items = list(result.scalars().all())

        return items, total

    async def get_all_clauses_for_document(
        self, document_id: uuid.UUID
    ) -> list[Clause]:
        """Fetch all clauses for a document ordered by page and creation."""
        result = await self.session.execute(
            select(Clause)
            .where(Clause.document_id == document_id)
            .order_by(Clause.page_number.nulls_last(), Clause.created_at)
        )
        return list(result.scalars().all())

    async def count_by_risk(self, document_id: uuid.UUID) -> dict[str, int]:
        """
        Calculate exact risk counts (HIGH, MEDIUM, LOW, TOTAL) strictly from stored clause records.
        """
        result = await self.session.execute(
            select(Clause.risk_level, func.count(Clause.id))
            .where(Clause.document_id == document_id)
            .group_by(Clause.risk_level)
        )
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        total = 0
        for risk, count in result.all():
            if risk in counts:
                counts[risk] = count
            total += count
        counts["TOTAL"] = total
        return counts

    async def delete_clauses_by_document(self, document_id: uuid.UUID) -> int:
        """Delete all existing clauses for a document (used during re-analysis)."""
        result = await self.session.execute(
            select(Clause).where(Clause.document_id == document_id)
        )
        clauses = result.scalars().all()
        count = len(clauses)
        for c in clauses:
            await self.session.delete(c)
        await self.session.flush()
        return count

"""
Analysis repository — database operations for analysis_summaries.
"""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis_summary import AnalysisSummary


class AnalysisRepository:
    """Encapsulates DB operations for the AnalysisSummary model."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_summary_by_document(
        self, document_id: uuid.UUID
    ) -> AnalysisSummary | None:
        """Fetch the analysis summary for a specific document."""
        result = await self.session.execute(
            select(AnalysisSummary).where(
                AnalysisSummary.document_id == document_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert_summary(
        self,
        document_id: uuid.UUID,
        total_clauses: int,
        high_count: int,
        medium_count: int,
        low_count: int,
        overall_summary: str,
    ) -> AnalysisSummary:
        """Create or update analysis summary for a document."""
        summary = await self.get_summary_by_document(document_id)
        if summary:
            summary.total_clauses = total_clauses
            summary.high_count = high_count
            summary.medium_count = medium_count
            summary.low_count = low_count
            summary.overall_summary = overall_summary
        else:
            summary = AnalysisSummary(
                document_id=document_id,
                total_clauses=total_clauses,
                high_count=high_count,
                medium_count=medium_count,
                low_count=low_count,
                overall_summary=overall_summary,
            )
            self.session.add(summary)

        await self.session.flush()
        return summary

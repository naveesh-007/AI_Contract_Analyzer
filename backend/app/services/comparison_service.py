"""
Standard Clause Comparison Service (SRS-S02).
Orchestrates benchmark matching, deviation scoring, difference identification,
and persistence.
"""
import logging
import re
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clause import Clause
from app.models.comparison import StandardClause, StandardContractTemplate
from app.models.document import Document
from app.repositories.clause_repo import ClauseRepository
from app.repositories.comparison_repo import ComparisonRepository
from app.repositories.document_repo import DocumentRepository
from app.schemas.comparison import (
    ClauseComparisonItemOut,
    ComparisonSummaryStats,
    DeviationLevel,
    DocumentComparisonResponse,
)
from app.services.embedding_service import EmbeddingService, cosine_similarity
from app.services.llm_service import LLMService

logger = logging.getLogger(__name__)


# Mapping of common clause category keywords for heuristic matching
CATEGORY_KEYWORDS = {
    "PAYMENT": ["rent", "payment", "invoice", "fee", "compensation", "billing", "grace period", "deposit", "late fee", "price"],
    "TERMINATION": ["termination", "terminate", "cancel", "cancellation", "cure period", "default", "breach", "expiration"],
    "RENEWAL": ["renew", "renewal", "extension", "month-to-month", "term of lease", "auto-renew"],
    "SECURITY_DEPOSIT": ["deposit", "security deposit", "deduction", "wear and tear", "escrow"],
    "MAINTENANCE": ["maintenance", "repair", "habitability", "condition of premises", "cleanliness"],
    "ENTRY": ["entry", "access", "inspection", "showing", "24 hour", "landlord entry"],
    "LIABILITY": ["liability", "limitation of liability", "indemnif", "damages", "hold harmless", "loss", "negligence", "disclaimer", "warranty"],
    "INTELLECTUAL_PROPERTY": ["intellectual property", "ip", "ownership", "work for hire", "copyright", "deliverable", "license", "user content"],
    "CONFIDENTIALITY": ["confidential", "non-disclosure", "nda", "proprietary", "trade secret", "survival"],
    "DISPUTE_RESOLUTION": ["dispute", "governing law", "jurisdiction", "arbitration", "informal resolution", "court", "venue"],
    "MODIFICATION": ["amendment", "modification", "change order", "change to terms", "revision"],
    "SCOPE": ["scope", "services", "deliverables", "milestones", "work done"],
}


class ComparisonService:
    """Coordinates standard benchmark retrieval and clause deviation comparison."""

    def __init__(
        self,
        session: AsyncSession,
        llm_service: Optional[LLMService] = None,
        embedding_service: Optional[EmbeddingService] = None,
    ) -> None:
        self.session = session
        self.comparison_repo = ComparisonRepository(session)
        self.doc_repo = DocumentRepository(session)
        self.clause_repo = ClauseRepository(session)
        self.llm_service = llm_service or LLMService()
        self.embedding_service = embedding_service or EmbeddingService()

    def _match_category(self, clause: Clause, benchmark_clauses: list[StandardClause]) -> tuple[StandardClause, str]:
        """
        Determines the closest benchmark clause for an actual contract clause
        using title match, keyword overlap, and category heuristics.
        """
        title = (clause.section_title or "").lower()
        num = (clause.section_number or "").lower()
        text = (clause.clause_text or "").lower()
        combined = f"{title} {num} {text[:300]}"

        best_match: Optional[StandardClause] = None
        best_score = -1

        for b_clause in benchmark_clauses:
            b_cat = b_clause.category.upper()
            keywords = CATEGORY_KEYWORDS.get(b_cat, [b_cat.lower()])

            score = 0
            # Title exact/partial match gets highest weight
            if b_clause.title.lower() in title or title in b_clause.title.lower():
                score += 15

            for kw in keywords:
                if kw in title:
                    score += 10
                if kw in combined:
                    score += 3

            if score > best_score:
                best_score = score
                best_match = b_clause

        # If no strong match found, fallback to first benchmark or general category
        matched_clause = best_match or benchmark_clauses[0]
        category = matched_clause.category if matched_clause else "GENERAL"
        return matched_clause, category

    async def compare_document_clauses(
        self, document_id: uuid.UUID
    ) -> DocumentComparisonResponse:
        """
        Executes end-to-end standard clause comparison for all clauses of a document:
        1. Loads document and its extracted clauses.
        2. Retrieves the benchmark template for document.document_type.
        3. Matches each clause to the most appropriate benchmark category.
        4. Compares actual text with benchmark text using LLM.
        5. Computes deviation level, similarity score, and differences.
        6. Persists comparisons to clause_comparisons table.
        7. Returns structured comparison response with metrics.
        """
        doc = await self.doc_repo.get_document(document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found.")

        # Ensure seed templates exist
        await self.comparison_repo.ensure_seed_templates()

        # Load clauses
        db_clauses, _ = await self.clause_repo.get_clauses_by_document(
            document_id=document_id, page_size=100
        )

        if not db_clauses:
            raise ValueError(
                f"No clauses found for document {document_id}. Run AI analysis first."
            )

        # Get standard template for document type
        template = await self.comparison_repo.get_template_by_document_type(doc.document_type)
        if not template or not template.clauses:
            # Fallback to general template
            template = await self.comparison_repo.get_template_by_document_type("Other")

        benchmark_clauses = template.clauses if template else []

        comparison_records: list[dict] = []

        for clause in db_clauses:
            if not benchmark_clauses:
                continue

            matched_benchmark, category = self._match_category(clause, benchmark_clauses)

            # Perform LLM comparison
            llm_result = await self.llm_service.compare_clause_to_benchmark(
                actual_clause_text=clause.clause_text,
                benchmark_clause_text=matched_benchmark.benchmark_text,
                category=category,
            )

            comparison_records.append(
                {
                    "clause_id": clause.id,
                    "standard_clause_id": matched_benchmark.id,
                    "category": category,
                    "deviation_level": llm_result.deviation_level.value,
                    "similarity_score": llm_result.similarity_score,
                    "comparison_summary": llm_result.comparison_summary,
                    "differences": llm_result.differences,
                }
            )

        # Persist to database
        db_comparisons = await self.comparison_repo.bulk_create_comparisons(
            document_id=document_id,
            comparison_records=comparison_records,
        )

        return await self.get_document_comparisons(document_id)

    async def get_document_comparisons(
        self,
        document_id: uuid.UUID,
        deviation_level: Optional[str] = None,
    ) -> DocumentComparisonResponse:
        """
        Retrieves stored comparisons for a document and computes summary metrics.
        """
        doc = await self.doc_repo.get_document(document_id)
        if not doc:
            raise ValueError(f"Document {document_id} not found.")

        template = await self.comparison_repo.get_template_by_document_type(doc.document_type)
        template_name = template.name if template else "Standard Commercial Benchmark"

        comparisons = await self.comparison_repo.get_comparisons_by_document(
            document_id=document_id,
            deviation_level=deviation_level,
        )

        items_out: list[ClauseComparisonItemOut] = []
        high_cnt = 0
        med_cnt = 0
        low_cnt = 0
        total_score = 0.0

        for comp in comparisons:
            dev = comp.deviation_level.upper()
            if dev == "HIGH":
                high_cnt += 1
            elif dev == "MEDIUM":
                med_cnt += 1
            else:
                low_cnt += 1

            total_score += comp.similarity_score

            actual_text = comp.clause.clause_text if comp.clause else ""
            sec_title = comp.clause.section_title if comp.clause else None
            sec_num = comp.clause.section_number if comp.clause else None
            page_num = comp.clause.page_number if comp.clause else 1

            bench_text = comp.standard_clause.benchmark_text if comp.standard_clause else "Standard industry benchmark provision."
            bench_title = comp.standard_clause.title if comp.standard_clause else "Standard Provision"

            diffs = comp.differences if isinstance(comp.differences, list) else []

            items_out.append(
                ClauseComparisonItemOut(
                    id=comp.id,
                    document_id=comp.document_id,
                    clause_id=comp.clause_id,
                    standard_clause_id=comp.standard_clause_id,
                    category=comp.category,
                    section_title=sec_title,
                    section_number=sec_num,
                    actual_clause=actual_text,
                    benchmark_clause=bench_text,
                    benchmark_title=bench_title,
                    deviation_level=DeviationLevel(comp.deviation_level),
                    similarity_score=comp.similarity_score,
                    comparison_summary=comp.comparison_summary,
                    differences=[str(d) for d in diffs],
                    page_number=page_num,
                    created_at=comp.created_at,
                )
            )

        total_cnt = len(comparisons)
        avg_sim = round(total_score / total_cnt, 2) if total_cnt > 0 else 0.0

        summary = ComparisonSummaryStats(
            total_comparisons=total_cnt,
            high_deviation=high_cnt,
            medium_deviation=med_cnt,
            low_deviation=low_cnt,
            average_similarity=avg_sim,
        )

        return DocumentComparisonResponse(
            document_id=doc.id,
            document_type=doc.document_type,
            template_name=template_name,
            summary=summary,
            comparisons=items_out,
        )

"""
Analysis Pipeline Service — orchestrates clause extraction, LLM risk assessment,
database persistence, and strict count summaries.
"""
import asyncio
import logging
import uuid
from typing import Optional

from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.clause_repo import ClauseRepository
from app.repositories.document_repo import DocumentRepository
from app.schemas.analysis import AnalysisResponse, AnalysisSummaryOut
from app.schemas.clause import ClauseOut
from app.services.chunking_service import ChunkingService
from app.services.clause_extraction import extract_clauses_from_pages
from app.services.llm_service import LLMService, LLMServiceError

logger = logging.getLogger(__name__)


class AnalysisPipelineError(Exception):
    """Raised when the document analysis pipeline encounters an error."""


class EmptyDocumentError(AnalysisPipelineError):
    """Raised when the document contains no extractable text."""


class AnalysisPipeline:
    """Coordinates the end-to-end legal document simplification and risk analysis."""

    def __init__(
        self,
        session: AsyncSession,
        llm_service: Optional[LLMService] = None,
    ) -> None:
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.clause_repo = ClauseRepository(session)
        self.analysis_repo = AnalysisRepository(session)
        self.llm_service = llm_service or LLMService()

    async def run(self, document_id: uuid.UUID) -> AnalysisResponse:
        """
        Executes the analysis pipeline:
        1. Fetch document and page texts
        2. Validate non-empty text
        3. Extract candidate clauses and section markers
        4. Perform LLM risk assessment & plain-language explanations
        5. Persist clauses to DB
        6. Compute exact risk counts strictly from persisted clauses
        7. Persist analysis summary to DB
        8. Mark document as ANALYZED
        """
        # 1. Fetch document with pages
        doc = await self.doc_repo.get_document_with_pages(document_id)
        if not doc:
            raise AnalysisPipelineError(f"Document {document_id} not found.")

        if not doc.pages or not any(p.text.strip() for p in doc.pages):
            raise EmptyDocumentError(
                f"Document {document_id} contains no text pages to analyze."
            )

        # 2. Extract candidate clauses
        candidates = extract_clauses_from_pages(doc.pages)
        if not candidates:
            raise EmptyDocumentError(
                f"No contractual clauses could be identified in document {document_id}."
            )

        candidate_dicts = [
            {
                "section_number": c.section_number,
                "section_title": c.section_title,
                "clause_text": c.clause_text,
                "page_number": c.page_number,
                "char_start": c.char_start,
                "char_end": c.char_end,
            }
            for c in candidates
        ]

        full_preview = " ".join(p.text for p in doc.pages)[:1500]

        # 3. Call LLM Service
        try:
            llm_result = await self.llm_service.analyze_clauses(
                candidate_clauses=candidate_dicts,
                document_text_summary=full_preview,
            )
        except LLMServiceError as exc:
            logger.error("LLM risk analysis failed for document %s: %s", document_id, exc)
            raise AnalysisPipelineError(f"AI Risk analysis failed: {exc}") from exc

        # 4. Reconcile LLM clauses with extracted offsets and page numbers
        # Clean up any existing clauses if re-analyzing
        await self.clause_repo.delete_clauses_by_document(document_id)

        clauses_to_persist = []
        for idx, item in enumerate(llm_result.clauses):
            # Match with candidate to preserve exact offsets
            matched_candidate = (
                candidates[idx] if idx < len(candidates) else None
            )

            char_start = (
                matched_candidate.char_start
                if matched_candidate
                else None
            )
            char_end = (
                matched_candidate.char_end
                if matched_candidate
                else None
            )
            page_num = (
                item.page_number
                or (matched_candidate.page_number if matched_candidate else 1)
            )

            clauses_to_persist.append(
                {
                    "section_number": item.section_number or (matched_candidate.section_number if matched_candidate else None),
                    "section_title": item.section_title or (matched_candidate.section_title if matched_candidate else None),
                    "clause_text": item.clause_text or (matched_candidate.clause_text if matched_candidate else ""),
                    "risk_level": item.risk_level,
                    "explanation": item.explanation,
                    "reason": item.reason,
                    "page_number": page_num,
                    "char_start": char_start,
                    "char_end": char_end,
                }
            )

        # 5. Persist clauses (with retry for SQLite lock contention)
        db_clauses = await self._flush_with_retry(
            self.clause_repo.bulk_create_clauses,
            document_id=document_id,
            clause_data_list=clauses_to_persist,
        )

        # Commit to release the SQLite write lock between major steps
        await self.session.commit()

        # 6. Strict risk counts calculated from stored clauses
        counts = await self.clause_repo.count_by_risk(document_id)
        total_clauses = counts.get("TOTAL", len(db_clauses))
        high_count = counts.get("HIGH", 0)
        medium_count = counts.get("MEDIUM", 0)
        low_count = counts.get("LOW", 0)

        # 7. Persist analysis summary
        db_summary = await self.analysis_repo.upsert_summary(
            document_id=document_id,
            total_clauses=total_clauses,
            high_count=high_count,
            medium_count=medium_count,
            low_count=low_count,
            overall_summary=llm_result.overall_summary,
        )

        # 8. Mark document as ANALYZED
        await self.doc_repo.update_status(document_id, "ANALYZED")
        await self.session.commit()

        # 8b. Pre-compute and persist document chunks & embeddings for RAG chat
        try:
            chunker = ChunkingService(self.session)
            await chunker.create_chunks_for_document(
                document_id=document_id,
                pages=doc.pages,
                clauses=db_clauses,
            )
            await self.session.commit()
        except Exception as exc:
            logger.warning("Chunk creation encountered non-fatal error: %s", exc)
            # Rollback only the failed chunk step, don't lose earlier work
            await self.session.rollback()

        # 8c. Pre-compute standard benchmark clause comparisons (SRS-S02)
        try:
            from app.services.comparison_service import ComparisonService
            comp_service = ComparisonService(self.session, self.llm_service)
            await comp_service.compare_document_clauses(document_id)
            await self.session.commit()
        except Exception as exc:
            logger.warning("Standard comparison pre-computation encountered non-fatal error: %s", exc)
            await self.session.rollback()


        summary_out = AnalysisSummaryOut(
            total_clauses=total_clauses,
            high=high_count,
            medium=medium_count,
            low=low_count,
            overall_summary=db_summary.overall_summary,
        )

        return AnalysisResponse(
            document_id=document_id,
            status="ANALYZED",
            summary=summary_out,
            clauses=[ClauseOut.model_validate(c) for c in db_clauses],
        )

    # ── SQLite retry helper ──────────────────────────────────────────────────

    _RETRY_MAX = 3
    _RETRY_DELAY = 0.5  # seconds — doubles each retry

    async def _flush_with_retry(self, coro_fn, **kwargs):
        """
        Call an async repository method with retry logic for transient
        SQLite 'database is locked' errors.
        """
        for attempt in range(self._RETRY_MAX):
            try:
                return await coro_fn(**kwargs)
            except OperationalError as exc:
                if "database is locked" in str(exc) and attempt < self._RETRY_MAX - 1:
                    logger.warning(
                        "SQLite locked (attempt %d/%d), retrying after %.1fs...",
                        attempt + 1, self._RETRY_MAX,
                        self._RETRY_DELAY * (2 ** attempt),
                    )
                    await asyncio.sleep(self._RETRY_DELAY * (2 ** attempt))
                    continue
                raise

"""
Analysis API routes.

POST /api/documents/{document_id}/analyze  — Run end-to-end clause extraction and AI risk assessment
GET  /api/documents/{document_id}/summary  — Get aggregated risk counts and plain-language summary
"""
import logging
import math
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.clause_repo import ClauseRepository
from app.repositories.document_repo import DocumentRepository
from app.schemas.analysis import AnalysisResponse, AnalysisSummaryOut
from app.schemas.clause import ClauseOut, PaginatedClausesResponse, RiskLevel
from app.services.analysis_pipeline import (
    AnalysisPipeline,
    AnalysisPipelineError,
    EmptyDocumentError,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Analysis & Clauses"])


# ─── POST /api/documents/{document_id}/analyze ────────────────────────────────


@router.post(
    "/{document_id}/analyze",
    response_model=AnalysisResponse,
    status_code=status.HTTP_200_OK,
    summary="Run AI clause extraction and risk analysis on an uploaded document",
)
async def analyze_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisResponse:
    """
    Executes the AI analysis pipeline:
    1. Reads extracted text pages from document_pages
    2. Identifies sections, headings, and candidate contractual clauses
    3. Analyzes legal risks and generates plain-language explanations
    4. Persists clauses to the database
    5. Calculates strict counts (HIGH, MEDIUM, LOW) from stored clause records
    6. Persists analysis summary and marks document as ANALYZED
    """
    repo = DocumentRepository(db)
    doc = await repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    pipeline = AnalysisPipeline(db)
    try:
        result = await pipeline.run(document_id)
        return result
    except EmptyDocumentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except AnalysisPipelineError as exc:
        logger.error("Analysis pipeline error for %s: %s", document_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {exc}",
        )
    except Exception as exc:
        logger.exception("Unexpected error analyzing document %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during analysis: {exc}",
        )


# ─── GET /api/documents/{document_id}/summary ─────────────────────────────────


@router.get(
    "/{document_id}/summary",
    response_model=AnalysisSummaryOut,
    summary="Get aggregated risk summary for an analyzed document",
)
async def get_document_summary(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AnalysisSummaryOut:
    """
    Returns risk summary counts (total_clauses, high, medium, low, overall_summary).
    Counts are strictly calculated from stored clause records.
    """
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    analysis_repo = AnalysisRepository(db)
    clause_repo = ClauseRepository(db)

    summary = await analysis_repo.get_summary_by_document(document_id)
    counts = await clause_repo.count_by_risk(document_id)

    if not summary:
        if counts["TOTAL"] == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Analysis summary not found. Run /analyze first.",
            )
        # If clauses exist but summary row was not yet created, return calculated counts
        return AnalysisSummaryOut(
            total_clauses=counts["TOTAL"],
            high=counts["HIGH"],
            medium=counts["MEDIUM"],
            low=counts["LOW"],
            overall_summary="Analysis completed. Review individual clause details.",
        )

    return AnalysisSummaryOut(
        total_clauses=counts["TOTAL"],
        high=counts["HIGH"],
        medium=counts["MEDIUM"],
        low=counts["LOW"],
        overall_summary=summary.overall_summary,
    )


# ─── GET /api/documents/{document_id}/clauses ─────────────────────────────────


@router.get(
    "/{document_id}/clauses",
    response_model=PaginatedClausesResponse,
    summary="List analyzed clauses with risk filtering, search, and pagination",
)
async def get_document_clauses(
    document_id: uuid.UUID,
    risk_level: Optional[RiskLevel] = Query(
        default=None,
        description="Filter by risk level: LOW, MEDIUM, or HIGH",
    ),
    search: Optional[str] = Query(
        default=None,
        description="Search term in clause text, section title, explanation, or reason",
    ),
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(default=20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
) -> PaginatedClausesResponse:
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    clause_repo = ClauseRepository(db)
    items, total = await clause_repo.get_clauses_by_document(
        document_id=document_id,
        risk_level=risk_level,
        search=search,
        page=page,
        page_size=page_size,
    )

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedClausesResponse(
        items=[ClauseOut.model_validate(c) for c in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# ─── GET /api/documents/{document_id}/clauses/{clause_id} ─────────────────────


@router.get(
    "/{document_id}/clauses/{clause_id}",
    response_model=ClauseOut,
    summary="Get detailed information for a single clause",
)
async def get_single_clause(
    document_id: uuid.UUID,
    clause_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ClauseOut:
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    clause_repo = ClauseRepository(db)
    clause = await clause_repo.get_clause(clause_id)
    if not clause or clause.document_id != document_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Clause {clause_id} not found in document {document_id}.",
        )

    return ClauseOut.model_validate(clause)

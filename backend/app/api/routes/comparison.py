"""
Comparison API routes for Standard Clause Comparison (SRS-S02).

POST /api/documents/{document_id}/compare      — Execute/re-run benchmark comparison
GET  /api/documents/{document_id}/comparisons  — Retrieve stored comparisons with optional filtering
GET  /api/benchmarks/templates                 — List available benchmark templates
"""
import logging
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.comparison_repo import ComparisonRepository
from app.repositories.document_repo import DocumentRepository
from app.schemas.comparison import (
    DeviationLevel,
    DocumentComparisonResponse,
    StandardTemplateOut,
)
from app.services.comparison_service import ComparisonService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Standard Clause Comparison"])


# ─── POST /api/documents/{document_id}/compare ───────────────────────────────


@router.post(
    "/documents/{document_id}/compare",
    response_model=DocumentComparisonResponse,
    status_code=status.HTTP_200_OK,
    summary="Run standard benchmark comparison on extracted contract clauses",
)
async def compare_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentComparisonResponse:
    """
    Executes standard benchmark comparison (SRS-S02):
    1. Loads document and its extracted clauses
    2. Identifies matching benchmark template for document_type
    3. Categorizes each clause and compares against standard benchmark wording
    4. Calculates deviation levels (LOW, MEDIUM, HIGH) and similarity scores
    5. Identifies specific differences and plain-language summary
    6. Persists comparisons to database scoped by document_id
    """
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    service = ComparisonService(db)
    try:
        response = await service.compare_document_clauses(document_id)
        return response
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.exception("Error executing comparison for document %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Standard comparison failed: {exc}",
        )


# ─── GET /api/documents/{document_id}/comparisons ────────────────────────────


@router.get(
    "/documents/{document_id}/comparisons",
    response_model=DocumentComparisonResponse,
    summary="Get standard clause comparisons for a document with optional deviation filtering",
)
async def get_document_comparisons(
    document_id: uuid.UUID,
    deviation_level: Optional[DeviationLevel] = Query(
        default=None,
        description="Filter by deviation level: LOW, MEDIUM, or HIGH",
    ),
    db: AsyncSession = Depends(get_db),
) -> DocumentComparisonResponse:
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id} not found.",
        )

    service = ComparisonService(db)
    try:
        result = await service.get_document_comparisons(
            document_id=document_id,
            deviation_level=deviation_level.value if deviation_level else None,
        )
        if result.summary.total_comparisons == 0 and not deviation_level:
            # Auto-trigger comparison if not yet generated
            result = await service.compare_document_clauses(document_id)
        return result
    except Exception as exc:
        logger.exception("Failed to retrieve comparisons for document %s", document_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch comparisons: {exc}",
        )


# ─── GET /api/benchmarks/templates ───────────────────────────────────────────


@router.get(
    "/benchmarks/templates",
    response_model=list[StandardTemplateOut],
    summary="List available standard benchmark templates and archetype clauses",
)
async def list_benchmark_templates(
    db: AsyncSession = Depends(get_db),
) -> list[StandardTemplateOut]:
    repo = ComparisonRepository(db)
    templates = await repo.get_all_templates()
    return [StandardTemplateOut.model_validate(t) for t in templates]

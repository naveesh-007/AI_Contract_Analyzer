"""
Document API routes.

POST /api/documents/upload       — Upload + extract + persist
GET  /api/documents/{id}         — Document metadata
GET  /api/documents/{id}/text    — Page-level extracted text
"""
import logging
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.repositories.document_repo import DocumentRepository
from app.repositories.analysis_repo import AnalysisRepository
from app.repositories.clause_repo import ClauseRepository
from app.schemas.document import DocumentOut, DocumentPageOut, DocumentTextResponse, UploadResponse
from app.services.extraction import ExtractionError, extract_document
from app.services.report_generator import generate_pdf_report
from app.services.storage import delete_upload, save_upload
from app.utils.file_validation import FileValidationError, sanitize_filename, validate_upload
from fastapi.responses import Response

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])


# ── Upload ────────────────────────────────────────────────────────────────────


@router.post(
    "/upload",
    response_model=UploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a PDF or TXT document for extraction",
)
async def upload_document(
    file: UploadFile,
    document_type: str = Form(default="Other"),
    db: AsyncSession = Depends(get_db),
) -> UploadResponse:
    """
    Upload flow:
    1. Validate extension, MIME type, size, empty file
    2. Sanitize filename
    3. Save to uploads/
    4. Create document record (status=UPLOADED)
    5. Extract text (PDF page-by-page / TXT as single page)
    6. Save pages to document_pages
    7. Update status → ANALYZED (or FAILED on error)
    8. Return document_id
    """

    # ── Validate ──────────────────────────────────────────────────────────────
    try:
        await validate_upload(file)
    except FileValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    safe_name = sanitize_filename(file.filename or "upload")
    ext = os.path.splitext(safe_name)[1].lower().lstrip(".")  # "pdf" or "txt"

    # Validate document_type against allowed values
    allowed_types = {"Rental Agreement", "Freelance Contract", "Terms of Service", "Other"}
    if document_type not in allowed_types:
        document_type = "Other"

    # ── Save file ─────────────────────────────────────────────────────────────
    try:
        saved_path, file_size = await save_upload(file, safe_name)
    except OSError as exc:
        logger.error("Failed to save upload: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to store uploaded file.")

    # ── Persist document record ───────────────────────────────────────────────
    repo = DocumentRepository(db)
    doc = await repo.create_document(
        filename=safe_name,
        document_type=document_type,
        file_type=ext,
        file_size=file_size,
        status="UPLOADED",
    )

    # ── Extract text ──────────────────────────────────────────────────────────
    try:
        await repo.update_status(doc.id, "PROCESSING")
        pages = extract_document(Path(saved_path), ext)
        await repo.save_pages(doc.id, pages)
        await repo.update_status(doc.id, "ANALYZED")
        logger.info(
            "Document %s extracted successfully — %d page(s)", doc.id, len(pages)
        )
    except ExtractionError as exc:
        logger.warning("Extraction failed for %s: %s", doc.id, exc)
        await repo.update_status(doc.id, "FAILED")
        # Don't delete the file — keep for debugging
        raise HTTPException(
            status_code=422,
            detail=f"File uploaded but text extraction failed: {exc}",
        )
    except Exception as exc:
        logger.exception("Unexpected error during extraction for %s", doc.id)
        await repo.update_status(doc.id, "FAILED")
        raise HTTPException(status_code=500, detail="Unexpected extraction error.")

    return UploadResponse(
        document_id=doc.id,
        filename=doc.filename,
        document_type=doc.document_type,  # type: ignore[arg-type]
        status="ANALYZED",
    )


# ── Get document metadata ─────────────────────────────────────────────────────


@router.get(
    "/{document_id}",
    response_model=DocumentOut,
    summary="Get document metadata and processing status",
)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentOut:
    repo = DocumentRepository(db)
    doc = await repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return DocumentOut.model_validate(doc)


# ── Get document text ─────────────────────────────────────────────────────────


@router.get(
    "/{document_id}/text",
    response_model=DocumentTextResponse,
    summary="Get page-level extracted text for a document",
)
async def get_document_text(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> DocumentTextResponse:
    repo = DocumentRepository(db)
    doc = await repo.get_document_with_pages(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    if doc.status == "UPLOADED" or doc.status == "PROCESSING":
        raise HTTPException(
            status_code=409,
            detail=f"Document is still being processed (status: {doc.status}).",
        )
    if doc.status == "FAILED":
        raise HTTPException(
            status_code=422,
            detail="Document processing failed. No text available.",
        )

    return DocumentTextResponse(
        document_id=doc.id,
        total_pages=len(doc.pages),
        pages=[DocumentPageOut.model_validate(p) for p in doc.pages],
    )


# ── Download PDF Report ───────────────────────────────────────────────────────


@router.get(
    "/{document_id}/report",
    summary="Download executive risk analysis PDF report",
)
async def download_document_report(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    analysis_repo = AnalysisRepository(db)
    clause_repo = ClauseRepository(db)

    summary = await analysis_repo.get_summary_by_document(document_id)
    clauses, _ = await clause_repo.get_clauses_by_document(document_id=document_id, page_size=100)

    try:
        pdf_bytes = generate_pdf_report(document=doc, summary=summary, clauses=clauses)
    except Exception as exc:
        logger.exception("Failed to generate PDF report for document %s", document_id)
        raise HTTPException(status_code=500, detail=f"PDF generation failed: {exc}")

    report_filename = f"Risk_Report_{doc.filename.replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_filename}"'},
    )


# ── Delete Document ───────────────────────────────────────────────────────────


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a document and all associated pages, clauses, and chat history",
)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    doc = await repo.get_document(document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")

    await repo.delete_document(document_id)


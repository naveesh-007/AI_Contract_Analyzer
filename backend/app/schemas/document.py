"""
Pydantic schemas for request validation and API response serialization.
"""
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ─── Enums / Literals ────────────────────────────────────────────────────────

DocumentStatus = Literal["UPLOADED", "PROCESSING", "ANALYZED", "FAILED"]

DocumentType = Literal[
    "Rental Agreement",
    "Freelance Contract",
    "Terms of Service",
    "Other",
]

# ─── Upload ───────────────────────────────────────────────────────────────────


class UploadResponse(BaseModel):
    """Returned immediately after a successful file upload."""

    document_id: uuid.UUID
    filename: str
    document_type: DocumentType
    status: DocumentStatus


# ─── Document ─────────────────────────────────────────────────────────────────


class DocumentOut(BaseModel):
    """Full document metadata — returned by GET /api/documents/{id}."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    filename: str
    document_type: str
    file_type: str
    file_size: int
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime


# ─── Document Pages ───────────────────────────────────────────────────────────


class DocumentPageOut(BaseModel):
    """Single extracted page."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    page_number: int
    text: str
    char_start: int | None
    char_end: int | None


class DocumentTextResponse(BaseModel):
    """Returned by GET /api/documents/{id}/text."""

    document_id: uuid.UUID
    total_pages: int
    pages: list[DocumentPageOut]


# ─── Health ───────────────────────────────────────────────────────────────────


class HealthResponse(BaseModel):
    status: str = Field(default="ok")

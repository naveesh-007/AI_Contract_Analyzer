"""
Pydantic schemas for clauses and clause filtering/pagination.
"""
import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]


class ClauseBase(BaseModel):
    section_number: Optional[str] = None
    section_title: Optional[str] = None
    clause_text: str
    risk_level: RiskLevel
    explanation: str
    reason: str
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None


class ClauseCreate(ClauseBase):
    document_id: uuid.UUID


class ClauseOut(ClauseBase):
    """Returned by clause APIs."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    created_at: Optional[datetime] = None


class PaginatedClausesResponse(BaseModel):
    """Paginated list of clauses."""

    items: list[ClauseOut]
    total: int = Field(ge=0, description="Total matching clauses count")
    page: int = Field(ge=1, default=1, description="Current page number (1-indexed)")
    page_size: int = Field(ge=1, default=20, description="Number of items per page")
    total_pages: int = Field(ge=0, description="Total number of pages")

"""
Pydantic schemas for document risk analysis, summaries, and LLM structured output.
"""
import uuid
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.clause import ClauseOut, RiskLevel


class LLMClauseItem(BaseModel):
    """Single clause item inside LLM structured JSON output."""

    section_number: Optional[str] = None
    section_title: Optional[str] = None
    clause_text: str = Field(..., description="Verbatim contractual text")
    risk_level: RiskLevel = Field(..., description="Risk rating: LOW, MEDIUM, or HIGH")
    explanation: str = Field(
        ...,
        description="Plain-language explanation understandable to non-lawyers with cautious language",
    )
    reason: str = Field(..., description="Specific risk justification or flags")
    page_number: Optional[int] = Field(default=None, description="1-indexed page number")


class LLMAnalysisResult(BaseModel):
    """Structured response expected from the LLM provider."""

    overall_summary: str = Field(
        ...,
        description="Overall assessment and plain-language synthesis of document risks",
    )
    clauses: list[LLMClauseItem] = Field(
        default_factory=list,
        description="Extracted and classified contractual clauses",
    )


class AnalysisSummaryOut(BaseModel):
    """
    Returned by GET /api/documents/{document_id}/summary.
    Counts are strictly calculated from stored clause records.
    """

    model_config = ConfigDict(from_attributes=True)

    total_clauses: int = Field(ge=0, description="Total number of clauses")
    high: int = Field(ge=0, description="Count of HIGH risk clauses")
    medium: int = Field(ge=0, description="Count of MEDIUM risk clauses")
    low: int = Field(ge=0, description="Count of LOW risk clauses")
    overall_summary: str = Field(description="Plain-language overall summary")


class AnalysisResponse(BaseModel):
    """Returned by POST /api/documents/{document_id}/analyze."""

    document_id: uuid.UUID
    status: str
    summary: AnalysisSummaryOut
    clauses: list[ClauseOut]

"""
Pydantic schemas for Standard Clause Comparison (SRS-S02).
"""
import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class DeviationLevel(str, Enum):
    """Deviation levels for contract clause comparisons."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class StandardClauseOut(BaseModel):
    """Public schema for a benchmark standard clause."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    template_id: uuid.UUID
    category: str
    title: str
    benchmark_text: str
    description: Optional[str] = None


class StandardTemplateOut(BaseModel):
    """Public schema for a standard contract archetype benchmark template."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_type: str
    name: str
    description: str
    version: str
    clauses: list[StandardClauseOut] = []


class ClauseComparisonItemOut(BaseModel):
    """Individual clause comparison item with benchmark and deviation details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    document_id: uuid.UUID
    clause_id: uuid.UUID
    standard_clause_id: Optional[uuid.UUID] = None
    category: str
    section_title: Optional[str] = None
    section_number: Optional[str] = None
    actual_clause: str
    benchmark_clause: str
    benchmark_title: Optional[str] = None
    deviation_level: DeviationLevel
    similarity_score: float = Field(ge=0.0, le=1.0)
    comparison_summary: str
    differences: list[str] = []
    page_number: Optional[int] = 1
    created_at: datetime


class ComparisonSummaryStats(BaseModel):
    """Aggregated metrics for standard clause comparisons."""
    total_comparisons: int = 0
    high_deviation: int = 0
    medium_deviation: int = 0
    low_deviation: int = 0
    average_similarity: float = 0.0


class DocumentComparisonResponse(BaseModel):
    """Full API response for document clause comparison."""
    document_id: uuid.UUID
    document_type: str
    template_name: str
    summary: ComparisonSummaryStats
    comparisons: list[ClauseComparisonItemOut]


class LLMComparisonResult(BaseModel):
    """Structured output validated from LLM clause comparison analysis."""
    deviation_level: DeviationLevel
    similarity_score: float = Field(ge=0.0, le=1.0)
    comparison_summary: str
    differences: list[str] = Field(default_factory=list)

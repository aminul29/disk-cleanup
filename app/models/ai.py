from __future__ import annotations

from pydantic import BaseModel, Field


class AiCategorySummary(BaseModel):
    name: str
    risk_level: str
    total_bytes: int
    file_count: int
    selected_by_default: bool
    reason: str


class AiScanSummaryRequest(BaseModel):
    total_files_scanned: int
    total_bytes_scanned: int
    safe_bytes: int
    review_bytes: int
    protected_bytes: int
    large_file_count: int
    duplicate_group_count: int
    error_count: int
    categories: list[AiCategorySummary] = Field(default_factory=list)


class AiRecommendation(BaseModel):
    summary: str
    recommended_next_steps: list[str] = Field(default_factory=list)
    safety_notes: list[str] = Field(default_factory=list)
    review_priorities: list[str] = Field(default_factory=list)
    safe_cleanup_plan: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    confidence: str = "Medium"

from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class RiskLevel(str, Enum):
    SAFE = "Safe"
    REVIEW = "Review"
    PROTECTED = "Protected"


class CleanupItem(BaseModel):
    id: str
    file_name: str
    file_path: str
    extension: str
    size_bytes: int
    last_modified_at: datetime | None
    category: str
    risk_level: RiskLevel
    reason: str
    can_delete: bool
    is_selected: bool = False


class CleanupCategory(BaseModel):
    id: str
    name: str
    description: str
    risk_level: RiskLevel
    total_bytes: int = 0
    file_count: int = 0
    items: list[CleanupItem] = Field(default_factory=list)
    is_selected_by_default: bool = False


class DuplicateGroup(BaseModel):
    id: str
    file_size_bytes: int
    hash: str
    files: list[CleanupItem]
    suggested_keep_file_path: str
    potential_savings_bytes: int


class ScanResult(BaseModel):
    scan_id: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float
    total_files_scanned: int
    total_bytes_scanned: int
    safe_bytes: int
    review_bytes: int
    protected_bytes: int
    categories: list[CleanupCategory] = Field(default_factory=list)
    large_files: list[CleanupItem] = Field(default_factory=list)
    duplicate_groups: list[DuplicateGroup] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CleanupResult(BaseModel):
    scan_id: str
    started_at: datetime
    completed_at: datetime
    files_deleted: int
    files_skipped: int
    bytes_recovered: int
    categories_cleaned: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CleanupReport(BaseModel):
    report_id: str
    scan_id: str
    created_at: datetime
    files_deleted: int
    files_skipped: int
    bytes_recovered: int
    categories_cleaned: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    summary: str


class LicenseStatus(BaseModel):
    plan_name: str
    is_pro: bool
    enabled_features: list[str] = Field(default_factory=list)


class ScanHistoryItem(BaseModel):
    scan_id: str
    started_at: datetime
    completed_at: datetime | None
    duration_seconds: float
    total_files_scanned: int
    total_bytes_scanned: int
    safe_bytes: int
    review_bytes: int
    protected_bytes: int
    category_count: int
    large_file_count: int
    duplicate_group_count: int
    error_count: int

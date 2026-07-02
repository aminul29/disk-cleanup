from __future__ import annotations

from app.models import RiskLevel, ScanResult
from app.utils.formatting import format_bytes


class MockAiSummaryService:
    async def generate_scan_summary_async(self, result: ScanResult) -> str:
        if not result.categories:
            return "DiskWise has not scanned this device yet."

        largest_safe = max(
            (category for category in result.categories if category.risk_level == RiskLevel.SAFE),
            key=lambda category: category.total_bytes,
            default=None,
        )
        parts = [
            f"DiskWise found {format_bytes(result.safe_bytes)} safe to clean and {format_bytes(result.review_bytes)} that needs review.",
            "No personal documents were selected for cleanup.",
        ]
        if largest_safe and largest_safe.total_bytes > 0:
            parts.append(f"Most safe cleanup space is coming from {largest_safe.name.lower()}.")
        if result.large_files:
            parts.append("Large files were found, but they require manual review before any cleanup.")
        parts.append("DiskWise recommends cleaning safe items first.")
        return " ".join(parts)

    def generate_scan_summary(self, result: ScanResult) -> str:
        if not result.categories:
            return "DiskWise has not scanned this device yet."
        safe = format_bytes(result.safe_bytes)
        review = format_bytes(result.review_bytes)
        if result.safe_bytes == 0 and result.review_bytes == 0:
            return "DiskWise did not find obvious cleanup space in the scanned areas."
        return (
            f"DiskWise found {safe} of safe cleanup items and {review} of files "
            "that should be reviewed before deletion. No file names or paths were uploaded."
        )


# Future implementation:
# This service should call a backend service.
# The backend can call external AI providers.
# Never store external AI API keys inside the Windows app.

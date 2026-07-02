from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path

from app.models import CleanupItem, CleanupResult, RiskLevel
from app.services.report_service import ReportService
from app.utils.safety import is_safe_cleanup_path

try:
    from send2trash import send2trash
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    send2trash = None


class CleanupService:
    def __init__(
        self,
        report_service: ReportService,
        safe_roots: list[Path] | None = None,
        protected_roots: list[Path] | None = None,
    ) -> None:
        self.report_service = report_service
        self.safe_roots = safe_roots
        self.protected_roots = protected_roots

    def preview_items(self, items: list[CleanupItem]) -> list[CleanupItem]:
        return [
            item
            for item in items
            if item.is_selected and item.risk_level == RiskLevel.SAFE and item.can_delete
        ]

    def cleanup_safe_items(self, scan_id: str, items: list[CleanupItem]) -> CleanupResult:
        started_at = datetime.now()
        files_deleted = 0
        files_skipped = 0
        bytes_recovered = 0
        categories: set[str] = set()
        errors: list[str] = []

        for item in items:
            if item.risk_level != RiskLevel.SAFE or not item.can_delete:
                files_skipped += 1
                continue

            path = Path(item.file_path)
            if not self._is_safe_cleanup_path(path):
                files_skipped += 1
                errors.append(f"Skipped unsafe path: {item.file_name}")
                continue

            try:
                if not path.exists() or not path.is_file():
                    files_skipped += 1
                    continue
                if send2trash is not None:
                    send2trash(str(path))
                else:
                    path.unlink()
                files_deleted += 1
                bytes_recovered += item.size_bytes
                categories.add(item.category)
            except Exception as exc:
                files_skipped += 1
                errors.append(f"{item.file_name}: {exc}")

        completed_at = datetime.now()
        result = CleanupResult(
            scan_id=scan_id,
            started_at=started_at,
            completed_at=completed_at,
            files_deleted=files_deleted,
            files_skipped=files_skipped,
            bytes_recovered=bytes_recovered,
            categories_cleaned=sorted(categories),
            errors=errors,
        )
        self.report_service.create_cleanup_report(result)
        return result

    def _is_safe_cleanup_path(self, path: Path) -> bool:
        return is_safe_cleanup_path(path, self.safe_roots, self.protected_roots)

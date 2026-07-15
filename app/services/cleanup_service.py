from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path
from threading import Event
from typing import Callable

import psutil

from app.models import CleanupItem, CleanupResult, RiskLevel
from app.services.report_service import ReportService
from app.utils.safety import is_safe_cleanup_path

try:
    from send2trash import send2trash
except ImportError:  # pragma: no cover - dependency is declared in requirements.txt
    send2trash = None

CleanupProgressCallback = Callable[[int, int, str], None]


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
        self.logger = logging.getLogger(__name__)
        self.logger.info("Recycle Bin backend: %s", self.recycle_bin_backend_name())

    def recycle_bin_backend_name(self) -> str:
        if send2trash is None:
            return "unavailable"
        module_name = getattr(send2trash, "__module__", "")
        if module_name == "send2trash.win.modern":
            return "Windows IFileOperation"
        if module_name == "send2trash.win.legacy":
            return "legacy Windows shell"
        return module_name or "send2trash"

    def preview_items(self, items: list[CleanupItem]) -> list[CleanupItem]:
        return [
            item
            for item in items
            if item.is_selected and item.risk_level == RiskLevel.SAFE and item.can_delete
        ]

    def cleanup_safe_items(
        self,
        scan_id: str,
        items: list[CleanupItem],
        progress_callback: CleanupProgressCallback | None = None,
        cancel_event: Event | None = None,
    ) -> CleanupResult:
        started_at = datetime.now()
        started_perf = time.perf_counter()
        free_space_before = self._get_free_space()
        files_deleted = 0
        files_skipped = 0
        bytes_recovered = 0
        categories: set[str] = set()
        errors: list[str] = []
        deleted_item_ids: list[str] = []
        skipped_item_ids: list[str] = []
        canceled = False
        total_items = len(items)

        for index, item in enumerate(items):
            if cancel_event is not None and cancel_event.is_set():
                remaining = items[index:]
                files_skipped += len(remaining)
                skipped_item_ids.extend(remaining_item.id for remaining_item in remaining)
                errors.append(
                    f"Cleanup canceled. {len(remaining)} item(s) were not processed."
                )
                for remaining_item in remaining:
                    self._log_action(remaining_item, "canceled")
                canceled = True
                break

            if not item.is_selected or item.risk_level != RiskLevel.SAFE or not item.can_delete:
                files_skipped += 1
                skipped_item_ids.append(item.id)
                self._log_action(item, "blocked_by_selection_or_risk")
                self._emit_progress(progress_callback, index + 1, total_items, item.file_name)
                continue

            path = Path(item.file_path)
            if not self._is_safe_cleanup_path(path):
                files_skipped += 1
                skipped_item_ids.append(item.id)
                errors.append(f"Skipped unsafe path: {item.file_name}")
                self._log_action(item, "blocked_by_path_policy")
                self._emit_progress(progress_callback, index + 1, total_items, item.file_name)
                continue

            try:
                if not path.exists() or not path.is_file():
                    files_skipped += 1
                    skipped_item_ids.append(item.id)
                    self._log_action(item, "missing_or_not_a_file")
                    continue
                if send2trash is None:
                    raise RuntimeError("Recycle Bin support is unavailable")
                current_size = path.stat().st_size
                send2trash(str(path))
                if path.exists():
                    raise RuntimeError(
                        "Windows returned without moving this item to the Recycle Bin"
                    )
                files_deleted += 1
                bytes_recovered += current_size
                categories.add(item.category)
                deleted_item_ids.append(item.id)
                self._log_action(item, "moved_to_recycle_bin", current_size)
            except Exception as exc:
                files_skipped += 1
                skipped_item_ids.append(item.id)
                errors.append(f"{item.file_name}: {exc}")
                self._log_action(item, "failed")
            finally:
                self._emit_progress(progress_callback, index + 1, total_items, item.file_name)

        completed_at = datetime.now()
        duration_seconds = time.perf_counter() - started_perf
        free_space_after = self._get_free_space()
        result = CleanupResult(
            scan_id=scan_id,
            started_at=started_at,
            completed_at=completed_at,
            files_deleted=files_deleted,
            files_skipped=files_skipped,
            bytes_recovered=bytes_recovered,
            categories_cleaned=sorted(categories),
            errors=errors,
            deleted_item_ids=deleted_item_ids,
            skipped_item_ids=skipped_item_ids,
            canceled=canceled,
            duration_seconds=duration_seconds,
            free_space_before_bytes=free_space_before,
            free_space_after_bytes=free_space_after,
        )
        try:
            self.report_service.create_cleanup_report(result)
        except Exception as exc:
            result.errors.append(f"Cleanup report could not be saved: {exc}")
        self.logger.info(
            "Cleanup finished scan=%s deleted=%d skipped=%d bytes=%d duration=%.2fs canceled=%s",
            scan_id,
            files_deleted,
            files_skipped,
            bytes_recovered,
            duration_seconds,
            canceled,
        )
        return result

    def _is_safe_cleanup_path(self, path: Path) -> bool:
        return is_safe_cleanup_path(path, self.safe_roots, self.protected_roots)

    def _emit_progress(
        self,
        progress_callback: CleanupProgressCallback | None,
        completed: int,
        total: int,
        file_name: str,
    ) -> None:
        if progress_callback is not None:
            progress_callback(completed, total, file_name)

    def _get_free_space(self) -> int:
        try:
            root = Path.home().anchor or "C:/"
            return int(psutil.disk_usage(root).free)
        except OSError:
            return 0

    def _log_action(self, item: CleanupItem, outcome: str, size_bytes: int = 0) -> None:
        self.logger.info(
            "Cleanup action item=%s category=%s outcome=%s bytes=%d",
            item.id,
            item.category,
            outcome,
            size_bytes,
        )

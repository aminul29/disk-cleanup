from __future__ import annotations

import hashlib
import time
import uuid
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from threading import Event
from typing import Callable

import psutil

from app.models import CleanupCategory, CleanupItem, DuplicateGroup, RiskLevel, ScanResult
from app.services.settings_service import SettingsService
from app.utils.paths import (
    app_cache_locations,
    browser_cache_locations,
    downloads_path,
    is_under,
    personal_scan_locations,
    temp_locations,
    thumbnail_cache_locations,
)
from app.utils.safety import is_protected_path

ProgressCallback = Callable[[str, int, int, int], None]

MAX_SAFE_FILES_PER_CATEGORY = 8000
MAX_REVIEW_FILES_PER_CATEGORY = 3000
MAX_DUPLICATE_HASH_FILES = 500


class ScanService:
    def __init__(self, settings_service: SettingsService) -> None:
        self.settings_service = settings_service

    def get_disk_usage(self) -> dict[str, int | str]:
        root = Path.home().anchor or "C:/"
        usage = psutil.disk_usage(root)
        return {
            "drive": root,
            "total": int(usage.total),
            "used": int(usage.used),
            "free": int(usage.free),
            "percent": int(usage.percent),
        }

    def quick_scan(
        self,
        progress_callback: ProgressCallback | None = None,
        cancel_event: Event | None = None,
    ) -> ScanResult:
        started = datetime.now()
        start_perf = time.perf_counter()
        scan_id = f"scan_{started.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        errors: list[str] = []
        excluded = self.settings_service.get_excluded_folders()

        temp_items = self._scan_safe_locations(
            category="user_temp",
            locations=temp_locations(),
            reason="Temporary file in a user-level temp folder.",
            excluded=excluded,
            progress_name="User temporary files",
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            errors=errors,
        )
        browser_items = self._scan_safe_locations(
            category="browser_cache",
            locations=browser_cache_locations(),
            reason="Browser cache file stored under the user profile.",
            excluded=excluded,
            progress_name="Browser cache",
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            errors=errors,
        )
        thumbnail_items = self._scan_safe_locations(
            category="thumbnail_cache",
            locations=thumbnail_cache_locations(),
            reason="Windows thumbnail cache in a user-level Explorer cache folder.",
            excluded=excluded,
            progress_name="Thumbnail cache",
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            errors=errors,
            allowed_extensions={".db"},
        )
        app_cache_items = self._scan_safe_locations(
            category="app_cache",
            locations=app_cache_locations(),
            reason="User-level app cache or crash dump.",
            excluded=excluded,
            progress_name="App cache",
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            errors=errors,
            allowed_extensions={".tmp", ".temp", ".log", ".dmp", ".etl", ".cache"},
        )
        downloads_items = self._scan_old_downloads(
            excluded=excluded,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            errors=errors,
        )
        large_files = self._scan_large_files(
            excluded=excluded,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            errors=errors,
        )
        duplicate_groups = self._scan_duplicate_candidates(
            excluded=excluded,
            progress_callback=progress_callback,
            cancel_event=cancel_event,
            errors=errors,
        )

        categories = [
            self._build_category(
                "user_temp",
                "User Temporary Files",
                "Temporary files from user-level temp folders.",
                RiskLevel.SAFE,
                temp_items,
                True,
            ),
            self._build_category(
                "browser_cache",
                "Browser Cache",
                "Cache files from accessible browser profile folders.",
                RiskLevel.SAFE,
                browser_items,
                True,
            ),
            self._build_category(
                "old_downloads",
                "Old Downloads",
                "Large or old downloads that should be reviewed manually.",
                RiskLevel.REVIEW,
                downloads_items,
                False,
            ),
            self._build_category(
                "thumbnail_cache",
                "Thumbnail Cache",
                "Windows thumbnail cache files from the current user profile.",
                RiskLevel.SAFE,
                thumbnail_items,
                True,
            ),
            self._build_category(
                "app_cache",
                "User App Cache",
                "Crash dumps and app cache files in user-level cache folders.",
                RiskLevel.SAFE,
                app_cache_items,
                True,
            ),
            self._build_category(
                "large_files",
                "Large Files",
                "Files larger than 100 MB in common user folders.",
                RiskLevel.REVIEW,
                large_files,
                False,
            ),
            CleanupCategory(
                id="protected_personal_folders",
                name="Protected Personal Folders",
                description="Documents, Desktop, Pictures, Videos, Music, and source folders are protected.",
                risk_level=RiskLevel.PROTECTED,
                total_bytes=0,
                file_count=0,
                items=[],
                is_selected_by_default=False,
            ),
        ]

        total_files = sum(category.file_count for category in categories)
        total_bytes = sum(category.total_bytes for category in categories)
        safe_bytes = sum(
            category.total_bytes for category in categories if category.risk_level == RiskLevel.SAFE
        )
        review_bytes = sum(
            category.total_bytes for category in categories if category.risk_level == RiskLevel.REVIEW
        )
        protected_bytes = sum(
            category.total_bytes for category in categories if category.risk_level == RiskLevel.PROTECTED
        )
        completed = datetime.now()

        return ScanResult(
            scan_id=scan_id,
            started_at=started,
            completed_at=completed,
            duration_seconds=time.perf_counter() - start_perf,
            total_files_scanned=total_files,
            total_bytes_scanned=total_bytes,
            safe_bytes=safe_bytes,
            review_bytes=review_bytes,
            protected_bytes=protected_bytes,
            categories=categories,
            large_files=large_files,
            duplicate_groups=duplicate_groups,
            errors=errors,
        )

    def _scan_safe_locations(
        self,
        category: str,
        locations: list[Path],
        reason: str,
        excluded: list[Path],
        progress_name: str,
        progress_callback: ProgressCallback | None,
        cancel_event: Event | None,
        errors: list[str],
        allowed_extensions: set[str] | None = None,
    ) -> list[CleanupItem]:
        items: list[CleanupItem] = []
        total_bytes = 0
        for location in locations:
            for file_path in self._walk_files(location, excluded, cancel_event, errors):
                if cancel_event and cancel_event.is_set():
                    break
                if len(items) >= MAX_SAFE_FILES_PER_CATEGORY:
                    errors.append(f"Scan limit reached for {progress_name}. Remaining files were skipped.")
                    return items
                if allowed_extensions and file_path.suffix.lower() not in allowed_extensions:
                    continue
                if is_protected_path(file_path):
                    continue
                item = self._create_item(file_path, category, RiskLevel.SAFE, reason, True)
                if item is None:
                    continue
                item.is_selected = True
                items.append(item)
                total_bytes += item.size_bytes
                self._emit_progress(progress_callback, progress_name, len(items), total_bytes, 20)
        return items

    def _scan_old_downloads(
        self,
        excluded: list[Path],
        progress_callback: ProgressCallback | None,
        cancel_event: Event | None,
        errors: list[str],
    ) -> list[CleanupItem]:
        downloads = downloads_path()
        if not downloads.exists():
            return []
        cutoff = datetime.now() - timedelta(days=90)
        target_extensions = {".exe", ".msi", ".zip", ".rar", ".7z", ".iso"}
        items: list[CleanupItem] = []
        total_bytes = 0
        for file_path in self._walk_files(downloads, excluded, cancel_event, errors):
            if len(items) >= MAX_REVIEW_FILES_PER_CATEGORY:
                errors.append("Scan limit reached for Downloads review. Remaining files were skipped.")
                break
            item = self._create_item(
                file_path,
                "old_downloads",
                RiskLevel.REVIEW,
                "Download is old, large, or commonly safe only after manual review.",
                False,
            )
            if item is None:
                continue
            is_old = item.last_modified_at is not None and item.last_modified_at < cutoff
            is_large = item.size_bytes >= 50 * 1024 * 1024
            is_target_type = item.extension.lower() in target_extensions
            if is_old or is_large or is_target_type:
                items.append(item)
                total_bytes += item.size_bytes
                self._emit_progress(
                    progress_callback,
                    "Downloads review",
                    len(items),
                    total_bytes,
                    45,
                )
        return items

    def _scan_large_files(
        self,
        excluded: list[Path],
        progress_callback: ProgressCallback | None,
        cancel_event: Event | None,
        errors: list[str],
    ) -> list[CleanupItem]:
        items: list[CleanupItem] = []
        total_bytes = 0
        min_size = 100 * 1024 * 1024
        for location in personal_scan_locations():
            for file_path in self._walk_files(location, excluded, cancel_event, errors):
                if len(items) >= MAX_REVIEW_FILES_PER_CATEGORY:
                    errors.append("Scan limit reached for Large files. Remaining files were skipped.")
                    return items
                item = self._create_item(
                    file_path,
                    "large_files",
                    RiskLevel.REVIEW,
                    "Large file in a personal folder. Review before deletion.",
                    False,
                )
                if item and item.size_bytes >= min_size:
                    items.append(item)
                    total_bytes += item.size_bytes
                    self._emit_progress(
                        progress_callback,
                        "Large files",
                        len(items),
                        total_bytes,
                        70,
                    )
        return items

    def _scan_duplicate_candidates(
        self,
        excluded: list[Path],
        progress_callback: ProgressCallback | None,
        cancel_event: Event | None,
        errors: list[str],
    ) -> list[DuplicateGroup]:
        size_groups: dict[int, list[Path]] = defaultdict(list)
        min_size = 1024 * 1024
        downloads = downloads_path()
        if not downloads.exists():
            return []

        for file_path in self._walk_files(downloads, excluded, cancel_event, errors):
            try:
                size = file_path.stat().st_size
            except OSError as exc:
                errors.append(f"Could not inspect duplicate candidate: {exc}")
                continue
            if size >= min_size:
                size_groups[size].append(file_path)

        groups: list[DuplicateGroup] = []
        hashed_files = 0
        for size, paths in size_groups.items():
            if len(paths) < 2:
                continue
            hash_groups: dict[str, list[CleanupItem]] = defaultdict(list)
            for file_path in paths:
                if hashed_files >= MAX_DUPLICATE_HASH_FILES:
                    errors.append("Duplicate scan hash limit reached. Remaining candidates were skipped.")
                    break
                file_hash = self._hash_file(file_path, errors)
                if not file_hash:
                    continue
                hashed_files += 1
                item = self._create_item(
                    file_path,
                    "duplicates",
                    RiskLevel.REVIEW,
                    "Duplicate candidate. Review all copies before deleting.",
                    False,
                )
                if item:
                    hash_groups[file_hash].append(item)
            for file_hash, files in hash_groups.items():
                if len(files) < 2:
                    continue
                suggested = min(
                    files,
                    key=lambda item: item.last_modified_at or datetime.max,
                )
                groups.append(
                    DuplicateGroup(
                        id=f"dup_{uuid.uuid4().hex[:10]}",
                        file_size_bytes=size,
                        hash=file_hash,
                        files=files,
                        suggested_keep_file_path=suggested.file_path,
                        potential_savings_bytes=size * (len(files) - 1),
                    )
                )
                self._emit_progress(
                    progress_callback,
                    "Duplicate candidates",
                    len(groups),
                    sum(group.potential_savings_bytes for group in groups),
                    90,
                )
        return groups

    def _walk_files(
        self,
        root: Path,
        excluded: list[Path],
        cancel_event: Event | None,
        errors: list[str],
    ):
        if any(is_under(root, excluded_path) or is_under(excluded_path, root) for excluded_path in excluded):
            return
        try:
            iterator = root.rglob("*")
            for path in iterator:
                if cancel_event and cancel_event.is_set():
                    return
                if any(is_under(path, excluded_path) for excluded_path in excluded):
                    continue
                try:
                    if path.is_file():
                        yield path
                except OSError as exc:
                    errors.append(f"Skipped inaccessible path: {exc}")
        except OSError as exc:
            errors.append(f"Could not scan {root}: {exc}")

    def _create_item(
        self,
        file_path: Path,
        category: str,
        risk_level: RiskLevel,
        reason: str,
        can_delete: bool,
    ) -> CleanupItem | None:
        try:
            stat = file_path.stat()
        except OSError:
            return None
        modified = datetime.fromtimestamp(stat.st_mtime)
        return CleanupItem(
            id=f"item_{uuid.uuid4().hex[:12]}",
            file_name=file_path.name,
            file_path=str(file_path),
            extension=file_path.suffix,
            size_bytes=int(stat.st_size),
            last_modified_at=modified,
            category=category,
            risk_level=risk_level,
            reason=reason,
            can_delete=can_delete and risk_level == RiskLevel.SAFE,
            is_selected=can_delete and risk_level == RiskLevel.SAFE,
        )

    def _build_category(
        self,
        category_id: str,
        name: str,
        description: str,
        risk_level: RiskLevel,
        items: list[CleanupItem],
        selected_by_default: bool,
    ) -> CleanupCategory:
        return CleanupCategory(
            id=category_id,
            name=name,
            description=description,
            risk_level=risk_level,
            total_bytes=sum(item.size_bytes for item in items),
            file_count=len(items),
            items=items,
            is_selected_by_default=selected_by_default,
        )

    def _hash_file(self, path: Path, errors: list[str]) -> str | None:
        digest = hashlib.sha256()
        try:
            with path.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
        except OSError as exc:
            errors.append(f"Could not hash duplicate candidate: {exc}")
            return None
        return digest.hexdigest()

    def _emit_progress(
        self,
        progress_callback: ProgressCallback | None,
        category: str,
        file_count: int,
        bytes_found: int,
        progress: int,
    ) -> None:
        if progress_callback:
            progress_callback(category, file_count, bytes_found, progress)

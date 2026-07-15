from __future__ import annotations

from pathlib import Path
from threading import Event

from app.database.local_database import LocalDatabase
from app.models import RiskLevel, ScanMode
from app.services import cleanup_service as cleanup_module
from app.services.cleanup_service import CleanupService
from app.services.report_service import ReportService
from app.services.scan_service import ScanService
from app.services.settings_service import SettingsService


def make_services(tmp_path: Path) -> tuple[ScanService, ReportService]:
    database = LocalDatabase(tmp_path / "diskwise-test.db")
    database.initialize()
    settings = SettingsService(database)
    return ScanService(settings), ReportService(database)


def test_quick_scan_cleanup_and_report_work_together(
    monkeypatch,
    tmp_path: Path,
) -> None:
    cache_root = tmp_path / "cache"
    recycle_root = tmp_path / "recycle-bin"
    cache_root.mkdir()
    recycle_root.mkdir()
    cache_file = cache_root / "stale.tmp"
    cache_file.write_bytes(b"safe cache data")
    protected_vault = cache_root / "passwords.kdbx"
    protected_vault.write_bytes(b"protected vault")

    monkeypatch.setattr("app.services.scan_service.temp_locations", lambda: [cache_root])
    monkeypatch.setattr("app.services.scan_service.browser_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.thumbnail_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.app_cache_locations", lambda: [])

    scan_service, report_service = make_services(tmp_path)
    scan = scan_service.quick_scan()
    report_service.save_scan(scan)

    safe_items = [
        item
        for category in scan.categories
        if category.risk_level == RiskLevel.SAFE
        for item in category.items
    ]
    assert scan.mode == ScanMode.QUICK
    assert len(safe_items) == 1
    assert safe_items[0].is_selected is True
    assert safe_items[0].can_delete is True

    def move_to_test_recycle_bin(path: str) -> None:
        source = Path(path)
        source.replace(recycle_root / source.name)

    monkeypatch.setattr(cleanup_module, "send2trash", move_to_test_recycle_bin)
    cleanup_service = CleanupService(
        report_service,
        safe_roots=[cache_root],
        protected_roots=[],
    )
    result = cleanup_service.cleanup_safe_items(scan.scan_id, safe_items)

    assert result.files_deleted == 1
    assert result.files_skipped == 0
    assert result.bytes_recovered == len(b"safe cache data")
    assert not cache_file.exists()
    assert (recycle_root / cache_file.name).exists()
    assert protected_vault.exists()

    stored_scans = report_service.list_scan_history()
    stored_reports = report_service.list_cleanup_reports()
    assert stored_scans[0].scan_id == scan.scan_id
    assert stored_reports[0].scan_id == scan.scan_id
    assert stored_reports[0].files_deleted == 1
    assert stored_reports[0].categories_cleaned == ["user_temp"]


def test_duplicate_detection_hashes_same_size_candidates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    payload = b"duplicate payload" * 70_000
    first = downloads / "first-copy.bin"
    second = downloads / "second-copy.bin"
    different = downloads / "different-copy.bin"
    first.write_bytes(payload)
    second.write_bytes(payload)
    different.write_bytes(b"x" * len(payload))

    monkeypatch.setattr("app.services.scan_service.downloads_path", lambda: downloads)
    scan_service, _ = make_services(tmp_path)
    groups = scan_service._scan_duplicate_candidates([], None, None, [])

    assert len(groups) == 1
    assert {item.file_name for item in groups[0].files} == {
        first.name,
        second.name,
    }
    assert groups[0].potential_savings_bytes == len(payload)
    assert all(item.risk_level == RiskLevel.REVIEW for item in groups[0].files)
    assert all(not item.is_selected and not item.can_delete for item in groups[0].files)


def test_quick_scan_honors_preexisting_cancellation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    (cache_root / "should-not-be-read.tmp").write_text("cache", encoding="utf-8")

    monkeypatch.setattr("app.services.scan_service.temp_locations", lambda: [cache_root])
    monkeypatch.setattr("app.services.scan_service.browser_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.thumbnail_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.app_cache_locations", lambda: [])

    scan_service, _ = make_services(tmp_path)
    cancel_event = Event()
    cancel_event.set()
    result = scan_service.quick_scan(cancel_event=cancel_event)

    assert result.canceled is True
    assert result.total_files_scanned == 0
    assert all(category.file_count == 0 for category in result.categories)

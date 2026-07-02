from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.database.local_database import LocalDatabase
from app.models import CleanupCategory, CleanupResult, RiskLevel, ScanResult
from app.services.report_service import ReportService


def test_cleanup_report_round_trips_through_sqlite(tmp_path: Path) -> None:
    database = LocalDatabase(tmp_path / "reports.db")
    database.initialize()
    reports = ReportService(database)
    result = CleanupResult(
        scan_id="scan_test",
        started_at=datetime.now(),
        completed_at=datetime.now(),
        files_deleted=2,
        files_skipped=1,
        bytes_recovered=512,
        categories_cleaned=["user_temp"],
        errors=["locked file"],
    )

    created = reports.create_cleanup_report(result)
    stored = reports.list_cleanup_reports()

    assert len(stored) == 1
    assert stored[0].report_id == created.report_id
    assert reports.latest_cleanup_report() is not None
    assert stored[0].bytes_recovered == 512
    assert stored[0].categories_cleaned == ["user_temp"]
    assert stored[0].errors == ["locked file"]


def test_scan_history_round_trips_through_sqlite(tmp_path: Path) -> None:
    database = LocalDatabase(tmp_path / "reports.db")
    database.initialize()
    reports = ReportService(database)
    now = datetime.now()
    scan = ScanResult(
        scan_id="scan_test",
        started_at=now,
        completed_at=now,
        duration_seconds=2.5,
        total_files_scanned=12,
        total_bytes_scanned=2048,
        safe_bytes=512,
        review_bytes=1536,
        protected_bytes=0,
        categories=[
            CleanupCategory(
                id="user_temp",
                name="User Temp",
                description="Temp files",
                risk_level=RiskLevel.SAFE,
                total_bytes=512,
                file_count=2,
                items=[],
                is_selected_by_default=True,
            )
        ],
        large_files=[],
        duplicate_groups=[],
        errors=["access denied"],
    )

    reports.save_scan(scan)
    stored = reports.list_scan_history()

    assert len(stored) == 1
    assert stored[0].scan_id == "scan_test"
    assert stored[0].total_files_scanned == 12
    assert stored[0].safe_bytes == 512
    assert stored[0].category_count == 1
    assert stored[0].error_count == 1
    assert reports.latest_scan() is not None


def test_scan_and_report_history_can_be_cleared_separately(tmp_path: Path) -> None:
    database = LocalDatabase(tmp_path / "reports.db")
    database.initialize()
    reports = ReportService(database)
    now = datetime.now()
    reports.save_scan(
        ScanResult(
            scan_id="scan_test",
            started_at=now,
            completed_at=now,
            duration_seconds=1.0,
            total_files_scanned=1,
            total_bytes_scanned=1,
            safe_bytes=1,
            review_bytes=0,
            protected_bytes=0,
            categories=[],
            large_files=[],
            duplicate_groups=[],
            errors=[],
        )
    )
    reports.create_cleanup_report(
        CleanupResult(
            scan_id="scan_test",
            started_at=now,
            completed_at=now,
            files_deleted=1,
            files_skipped=0,
            bytes_recovered=1,
            categories_cleaned=["user_temp"],
            errors=[],
        )
    )

    database.clear_scan_history()
    assert reports.list_scan_history() == []
    assert len(reports.list_cleanup_reports()) == 1

    database.clear_cleanup_reports()
    assert reports.list_cleanup_reports() == []

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
import sqlite3

from app.database.local_database import LocalDatabase
from app.models import CleanupCategory, CleanupResult, RiskLevel, ScanMode, ScanResult
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
        duration_seconds=3.25,
        free_space_before_bytes=10_000,
        free_space_after_bytes=10_512,
    )

    created = reports.create_cleanup_report(result)
    stored = reports.list_cleanup_reports()

    assert len(stored) == 1
    assert stored[0].report_id == created.report_id
    assert reports.latest_cleanup_report() is not None
    assert stored[0].bytes_recovered == 512
    assert stored[0].categories_cleaned == ["user_temp"]
    assert stored[0].errors == ["locked file"]
    assert stored[0].duration_seconds == 3.25
    assert stored[0].free_space_before_bytes == 10_000
    assert stored[0].free_space_after_bytes == 10_512


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
        mode=ScanMode.DEEP,
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
    assert stored[0].mode == ScanMode.DEEP
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


def test_legacy_scan_with_review_findings_is_inferred_as_deep(tmp_path: Path) -> None:
    database = LocalDatabase(tmp_path / "reports.db")
    database.initialize()
    now = datetime.now().isoformat()
    with database.connect() as connection:
        connection.execute(
            """
            INSERT INTO scan_history (
                scan_id, started_at, completed_at, duration_seconds,
                total_files_scanned, total_bytes_scanned, safe_bytes,
                review_bytes, protected_bytes, summary_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            ("legacy", now, now, 1.0, 2, 30, 10, 20, 0, json.dumps({})),
        )

    stored = ReportService(database).list_scan_history()

    assert stored[0].mode == ScanMode.DEEP


def test_initialize_migrates_legacy_cleanup_report_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy.db"
    with sqlite3.connect(db_path) as connection:
        connection.execute(
            """
            CREATE TABLE cleanup_reports (
                report_id TEXT PRIMARY KEY,
                scan_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                files_deleted INTEGER NOT NULL,
                files_skipped INTEGER NOT NULL,
                bytes_recovered INTEGER NOT NULL,
                categories_cleaned TEXT NOT NULL,
                errors TEXT NOT NULL,
                summary TEXT NOT NULL
            )
            """
        )

    database = LocalDatabase(db_path)
    database.initialize()

    with database.connect() as connection:
        columns = {
            row["name"] for row in connection.execute("PRAGMA table_info(cleanup_reports)")
        }
    assert {
        "duration_seconds",
        "free_space_before_bytes",
        "free_space_after_bytes",
        "canceled",
    } <= columns

from __future__ import annotations

import json
import uuid
from datetime import datetime

from app.database.local_database import LocalDatabase
from app.models import CleanupReport, CleanupResult, ScanHistoryItem, ScanResult
from app.utils.formatting import format_bytes


class ReportService:
    def __init__(self, database: LocalDatabase) -> None:
        self.database = database

    def save_scan(self, result: ScanResult) -> None:
        summary = {
            "category_count": len(result.categories),
            "large_file_count": len(result.large_files),
            "duplicate_group_count": len(result.duplicate_groups),
            "errors": result.errors,
        }
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO scan_history (
                    scan_id, started_at, completed_at, duration_seconds,
                    total_files_scanned, total_bytes_scanned, safe_bytes,
                    review_bytes, protected_bytes, summary_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.scan_id,
                    result.started_at.isoformat(),
                    result.completed_at.isoformat() if result.completed_at else None,
                    result.duration_seconds,
                    result.total_files_scanned,
                    result.total_bytes_scanned,
                    result.safe_bytes,
                    result.review_bytes,
                    result.protected_bytes,
                    json.dumps(summary),
                ),
            )

    def create_cleanup_report(self, result: CleanupResult) -> CleanupReport:
        report = CleanupReport(
            report_id=f"report_{uuid.uuid4().hex[:12]}",
            scan_id=result.scan_id,
            created_at=result.completed_at,
            files_deleted=result.files_deleted,
            files_skipped=result.files_skipped,
            bytes_recovered=result.bytes_recovered,
            categories_cleaned=result.categories_cleaned,
            errors=result.errors,
            summary=(
                f"Recovered {format_bytes(result.bytes_recovered)} from "
                f"{result.files_deleted} safe cleanup item(s)."
            ),
        )
        self.save_cleanup_report(report)
        return report

    def save_cleanup_report(self, report: CleanupReport) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO cleanup_reports (
                    report_id, scan_id, created_at, files_deleted, files_skipped,
                    bytes_recovered, categories_cleaned, errors, summary
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    report.report_id,
                    report.scan_id,
                    report.created_at.isoformat(),
                    report.files_deleted,
                    report.files_skipped,
                    report.bytes_recovered,
                    json.dumps(report.categories_cleaned),
                    json.dumps(report.errors),
                    report.summary,
                ),
            )

    def list_cleanup_reports(self) -> list[CleanupReport]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM cleanup_reports ORDER BY created_at DESC"
            ).fetchall()
        reports: list[CleanupReport] = []
        for row in rows:
            reports.append(
                CleanupReport(
                    report_id=row["report_id"],
                    scan_id=row["scan_id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    files_deleted=row["files_deleted"],
                    files_skipped=row["files_skipped"],
                    bytes_recovered=row["bytes_recovered"],
                    categories_cleaned=json.loads(row["categories_cleaned"]),
                    errors=json.loads(row["errors"]),
                    summary=row["summary"],
                )
            )
        return reports

    def latest_cleanup_report(self) -> CleanupReport | None:
        reports = self.list_cleanup_reports()
        return reports[0] if reports else None

    def list_scan_history(self) -> list[ScanHistoryItem]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT * FROM scan_history ORDER BY started_at DESC").fetchall()

        scans: list[ScanHistoryItem] = []
        for row in rows:
            summary = json.loads(row["summary_json"])
            scans.append(
                ScanHistoryItem(
                    scan_id=row["scan_id"],
                    started_at=datetime.fromisoformat(row["started_at"]),
                    completed_at=datetime.fromisoformat(row["completed_at"])
                    if row["completed_at"]
                    else None,
                    duration_seconds=row["duration_seconds"],
                    total_files_scanned=row["total_files_scanned"],
                    total_bytes_scanned=row["total_bytes_scanned"],
                    safe_bytes=row["safe_bytes"],
                    review_bytes=row["review_bytes"],
                    protected_bytes=row["protected_bytes"],
                    category_count=int(summary.get("category_count", 0)),
                    large_file_count=int(summary.get("large_file_count", 0)),
                    duplicate_group_count=int(summary.get("duplicate_group_count", 0)),
                    error_count=len(summary.get("errors", [])),
                )
            )
        return scans

    def latest_scan(self) -> ScanHistoryItem | None:
        scans = self.list_scan_history()
        return scans[0] if scans else None

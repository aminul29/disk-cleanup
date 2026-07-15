from __future__ import annotations

import os
from datetime import datetime
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.models import CleanupCategory, CleanupItem, RiskLevel, ScanResult
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.main_window import MainWindow


def test_dashboard_cleanup_command_opens_results_preview() -> None:
    events: list[tuple[str, int | None]] = []
    window = SimpleNamespace(
        nav=SimpleNamespace(
            setCurrentRow=lambda row: events.append(("navigate", row))
        ),
        results_page=SimpleNamespace(
            preview_cleanup=lambda: events.append(("preview", None))
        ),
    )

    MainWindow.open_cleanup_preview(window)

    assert events == [("navigate", 2), ("preview", None)]


def test_dashboard_keeps_live_cleanup_actions_enabled_after_history_refresh(
    tmp_path,
) -> None:
    app = QApplication.instance() or QApplication([])
    item = CleanupItem(
        id="live-safe-item",
        file_name="safe.tmp",
        file_path=str(tmp_path / "safe.tmp"),
        extension=".tmp",
        size_bytes=128,
        last_modified_at=datetime.now(),
        category="user_temp",
        risk_level=RiskLevel.SAFE,
        reason="Temporary file",
        can_delete=True,
        is_selected=True,
    )
    scan = ScanResult(
        scan_id="live-scan",
        started_at=datetime.now(),
        completed_at=datetime.now(),
        duration_seconds=1.0,
        total_files_scanned=1,
        total_bytes_scanned=item.size_bytes,
        safe_bytes=item.size_bytes,
        review_bytes=0,
        protected_bytes=0,
        categories=[
            CleanupCategory(
                id="user_temp",
                name="User Temporary Files",
                description="Temporary files",
                risk_level=RiskLevel.SAFE,
                total_bytes=item.size_bytes,
                file_count=1,
                items=[item],
                is_selected_by_default=True,
            )
        ],
    )
    settings = SimpleNamespace(ai_summary_enabled=lambda: False)
    report_service = SimpleNamespace(
        latest_scan=lambda: None,
        latest_cleanup_report=lambda: None,
    )
    page = DashboardPage(
        SimpleNamespace(
            get_disk_usage=lambda: {
                "drive": "C:\\",
                "total": 1000,
                "used": 500,
                "free": 500,
                "percent": 50,
            }
        ),
        report_service,
        SimpleNamespace(
            settings_service=settings,
            generate_scan_summary=lambda _scan: "Local summary",
        ),
    )

    page.set_scan_result(scan)
    report_service.latest_scan = lambda: SimpleNamespace()
    page.load_persisted_summary()

    assert page.view_results_button.isEnabled()
    assert page.clean_safe_button.isEnabled()

    page.deleteLater()
    app.processEvents()

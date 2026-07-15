from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEventLoop, Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialogButtonBox, QMessageBox, QTableWidget

from app.models import CleanupCategory, CleanupItem, CleanupResult, RiskLevel, ScanResult
from app.services import cleanup_service as cleanup_module
from app.services.cleanup_service import CleanupService
from app.ui.pages.results_page import CleanupPreviewDialog, ResultsPage


class FakeReportService:
    def create_cleanup_report(self, result):
        return None


def make_item(item_id: str, path: Path, size: int) -> CleanupItem:
    return CleanupItem(
        id=item_id,
        file_name=path.name,
        file_path=str(path),
        extension=path.suffix,
        size_bytes=size,
        last_modified_at=datetime.now(),
        category="user_temp",
        risk_level=RiskLevel.SAFE,
        reason="Temporary file",
        can_delete=True,
        is_selected=True,
    )


def test_results_remove_deleted_items_and_unselect_skipped_items(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    deleted = make_item("deleted", tmp_path / "deleted.tmp", 100)
    skipped = make_item("skipped", tmp_path / "skipped.tmp", 200)
    category = CleanupCategory(
        id="user_temp",
        name="User Temporary Files",
        description="Temporary files",
        risk_level=RiskLevel.SAFE,
        total_bytes=300,
        file_count=2,
        items=[deleted, skipped],
        is_selected_by_default=True,
    )
    scan = ScanResult(
        scan_id="scan_ui",
        started_at=datetime.now(),
        completed_at=datetime.now(),
        duration_seconds=1.0,
        total_files_scanned=2,
        total_bytes_scanned=300,
        safe_bytes=300,
        review_bytes=0,
        protected_bytes=0,
        categories=[category],
    )
    page = ResultsPage(
        CleanupService(FakeReportService(), safe_roots=[tmp_path], protected_roots=[]),
        SimpleNamespace(),
    )
    page.set_scan_result(scan)

    page.apply_cleanup_result(
        CleanupResult(
            scan_id=scan.scan_id,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            files_deleted=1,
            files_skipped=1,
            bytes_recovered=100,
            deleted_item_ids=[deleted.id],
            skipped_item_ids=[skipped.id],
        )
    )

    assert [item.id for item in category.items] == [skipped.id]
    assert skipped.is_selected is False
    assert category.file_count == 1
    assert category.total_bytes == 200
    assert scan.safe_bytes == 200
    assert scan.total_files_scanned == 1
    assert page.tree.topLevelItem(0).childCount() == 1
    assert page.tree.topLevelItem(0).child(0).checkState(0).value == 0

    page.deleteLater()
    app.processEvents()


def test_results_run_cleanup_in_background_and_reconcile_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    app = QApplication.instance() or QApplication([])
    safe_file = tmp_path / "background.tmp"
    safe_file.write_bytes(b"background cleanup")
    item = make_item("background", safe_file, safe_file.stat().st_size)
    category = CleanupCategory(
        id="user_temp",
        name="User Temporary Files",
        description="Temporary files",
        risk_level=RiskLevel.SAFE,
        total_bytes=item.size_bytes,
        file_count=1,
        items=[item],
        is_selected_by_default=True,
    )
    scan = ScanResult(
        scan_id="scan_background",
        started_at=datetime.now(),
        completed_at=datetime.now(),
        duration_seconds=1.0,
        total_files_scanned=1,
        total_bytes_scanned=item.size_bytes,
        safe_bytes=item.size_bytes,
        review_bytes=0,
        protected_bytes=0,
        categories=[category],
    )

    monkeypatch.setattr(cleanup_module, "send2trash", lambda path: Path(path).unlink())
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    page = ResultsPage(
        CleanupService(FakeReportService(), safe_roots=[tmp_path], protected_roots=[]),
        SimpleNamespace(),
    )
    page.set_scan_result(scan)
    completed: list[CleanupResult] = []
    event_loop = QEventLoop()
    page.cleanup_completed.connect(completed.append)
    page.cleanup_completed.connect(event_loop.quit)
    QTimer.singleShot(5000, event_loop.quit)

    page.start_cleanup([item])
    cleanup_thread = page.cleanup_thread
    event_loop.exec()
    assert cleanup_thread is not None
    cleanup_thread.wait(2000)
    app.processEvents()

    assert len(completed) == 1
    assert completed[0].files_deleted == 1
    assert not safe_file.exists()
    assert category.items == []
    assert scan.safe_bytes == 0
    assert page.preview_button.isEnabled() is False

    page.deleteLater()
    app.processEvents()


def test_results_selection_includes_safe_items_beyond_visible_tree_limit(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    items = [
        make_item(f"item-{index}", tmp_path / f"item-{index}.tmp", 1)
        for index in range(1001)
    ]
    category = CleanupCategory(
        id="user_temp",
        name="User Temporary Files",
        description="Temporary files",
        risk_level=RiskLevel.SAFE,
        total_bytes=len(items),
        file_count=len(items),
        items=items,
        is_selected_by_default=True,
    )
    scan = ScanResult(
        scan_id="scan_many",
        started_at=datetime.now(),
        completed_at=datetime.now(),
        duration_seconds=1.0,
        total_files_scanned=len(items),
        total_bytes_scanned=len(items),
        safe_bytes=len(items),
        review_bytes=0,
        protected_bytes=0,
        categories=[category],
    )
    page = ResultsPage(
        CleanupService(FakeReportService(), safe_roots=[tmp_path], protected_roots=[]),
        SimpleNamespace(),
    )
    page.set_scan_result(scan)

    assert len(page.selected_safe_items()) == 1001
    parent = page.tree.topLevelItem(0)
    assert parent.childCount() == 1001
    parent.setCheckState(0, Qt.CheckState.Unchecked)
    app.processEvents()
    assert page.selected_safe_items() == []
    assert not any(item.is_selected for item in items)

    page.deleteLater()
    app.processEvents()


def test_cleanup_preview_shows_location_and_recycle_bin_confirmation(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    item = make_item("preview", tmp_path / "preview.tmp", 64)
    dialog = CleanupPreviewDialog([item], 2, 1)

    table = dialog.findChild(QTableWidget)
    assert table is not None
    assert table.horizontalHeaderItem(1).text() == "Location"
    assert table.item(0, 1).text() == item.file_path
    assert table.item(0, 2).text() == "User Temp"
    assert table.verticalHeader().isHidden()
    assert "Recycle Bin" in dialog.confirm_checkbox.text()
    assert dialog.buttons.button(dialog.buttons.StandardButton.Ok).isEnabled() is False
    assert (
        dialog.buttons.button(QDialogButtonBox.StandardButton.Cancel).property("class")
        == "Secondary"
    )

    dialog.confirm_checkbox.setChecked(True)
    assert dialog.buttons.button(dialog.buttons.StandardButton.Ok).isEnabled() is True

    dialog.deleteLater()
    app.processEvents()

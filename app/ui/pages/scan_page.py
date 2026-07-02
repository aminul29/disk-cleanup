from __future__ import annotations

import time
from threading import Event

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models import ScanResult
from app.services.report_service import ReportService
from app.services.scan_service import ScanService
from app.ui.widgets import Card, StatCard, page_header
from app.utils.formatting import format_bytes, format_duration


SCAN_STAGES = [
    "User temporary files",
    "Browser cache",
    "Thumbnail cache",
    "App cache",
    "Downloads review",
    "Large files",
    "Duplicate candidates",
]


class ScanWorker(QObject):
    progress = Signal(str, int, int, int)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, scan_service: ScanService, report_service: ReportService, cancel_event: Event) -> None:
        super().__init__()
        self.scan_service = scan_service
        self.report_service = report_service
        self.cancel_event = cancel_event

    def run(self) -> None:
        try:
            result = self.scan_service.quick_scan(self.progress.emit, self.cancel_event)
            self.report_service.save_scan(result)
            self.completed.emit(result)
        except Exception as exc:  # pragma: no cover - UI safety net
            self.failed.emit(str(exc))


class ScanPage(QWidget):
    scan_completed = Signal(object)

    def __init__(self, scan_service: ScanService, report_service: ReportService) -> None:
        super().__init__()
        self.scan_service = scan_service
        self.report_service = report_service
        self.thread: QThread | None = None
        self.worker: ScanWorker | None = None
        self.cancel_event = Event()
        self.started_perf = 0.0
        self.stage_items: dict[str, QListWidgetItem] = {}
        self.current_stage_index = -1

        self.status_label = QLabel("Ready to scan local user-level cleanup locations.")
        self.status_label.setObjectName("MutedText")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.elapsed_card = StatCard("Elapsed", "0 sec", "No scan running")
        self.files_card = StatCard("Analyzed", "0", "Files found so far")
        self.space_card = StatCard("Found", "0 B", "Estimated reclaimable space")

        self.stage_list = QListWidget()
        self.stage_list.setObjectName("SettingsList")
        self.stage_list.setMinimumHeight(250)
        self._reset_stage_list()

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(120)

        self.start_button = QPushButton("Start Quick Scan")
        self.cancel_button = QPushButton("Cancel Scan")
        self.cancel_button.setProperty("class", "Secondary")
        self.cancel_button.setEnabled(False)

        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.update_elapsed)

        stats_grid = QGridLayout()
        stats_grid.setSpacing(12)
        stats_grid.addWidget(self.elapsed_card, 0, 0)
        stats_grid.addWidget(self.files_card, 0, 1)
        stats_grid.addWidget(self.space_card, 0, 2)

        controls = QWidget()
        controls_layout = QHBoxLayout(controls)
        controls_layout.setContentsMargins(0, 0, 0, 0)
        controls_layout.addWidget(self.start_button)
        controls_layout.addWidget(self.cancel_button)
        controls_layout.addStretch()

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)
        card_layout.addWidget(self.status_label)
        card_layout.addWidget(self.progress_bar)
        card_layout.addLayout(stats_grid)
        card_layout.addWidget(self.stage_list)
        card_layout.addWidget(controls)
        card_layout.addWidget(self.log)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)
        layout.addWidget(page_header("Smart Scan", "Track each scan stage while DiskWise analyzes local storage."))
        layout.addWidget(card)

        self.start_button.clicked.connect(self.start_scan)
        self.cancel_button.clicked.connect(self.cancel_scan)

    def start_scan(self) -> None:
        if self.thread is not None:
            self.status_label.setText("A scan is already running.")
            return

        self.cancel_event = Event()
        self.thread = QThread()
        self.worker = ScanWorker(self.scan_service, self.report_service, self.cancel_event)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self._clear_thread)

        self.started_perf = time.perf_counter()
        self.current_stage_index = -1
        self.progress_bar.setValue(0)
        self.log.clear()
        self._reset_stage_list()
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.status_label.setText("Scanning local user-level cleanup areas...")
        self.elapsed_card.set_values("0 sec", "Scan in progress")
        self.files_card.set_values("0", "Files found so far")
        self.space_card.set_values("0 B", "Estimated reclaimable space")
        self.timer.start()
        self.thread.start()

    def cancel_scan(self) -> None:
        self.cancel_event.set()
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Cancelling scan safely...")
        self._mark_current_stage("Cancelling")

    def on_progress(self, category: str, file_count: int, bytes_found: int, progress: int) -> None:
        self.progress_bar.setValue(min(progress, 99))
        self.status_label.setText(f"{category}: {file_count} item(s), {format_bytes(bytes_found)} found")
        self.files_card.set_values(f"{file_count:,}", f"Current stage: {category}")
        self.space_card.set_values(format_bytes(bytes_found), "Current stage estimate")
        self._activate_stage(category)

    def on_completed(self, result: ScanResult) -> None:
        self.timer.stop()
        self.progress_bar.setValue(100)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if self.cancel_event.is_set():
            self.status_label.setText("Scan cancelled. Partial results were saved safely.")
            self._mark_current_stage("Cancelled")
        else:
            self.status_label.setText("Scan complete.")
            self._complete_all_stages()

        self.elapsed_card.set_values(format_duration(result.duration_seconds), "Total scan duration")
        self.files_card.set_values(f"{result.total_files_scanned:,}", "Total files analyzed")
        self.space_card.set_values(
            format_bytes(result.safe_bytes + result.review_bytes),
            "Safe and review space found",
        )
        for error in result.errors[:10]:
            self.log.append(error)
        self.log.append(
            f"Found {format_bytes(result.safe_bytes)} safe to clean and {format_bytes(result.review_bytes)} for review."
        )
        self.scan_completed.emit(result)

    def on_failed(self, message: str) -> None:
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Scan could not complete.")
        self._mark_current_stage("Error")
        self.log.append(message)

    def update_elapsed(self) -> None:
        if self.started_perf <= 0:
            return
        self.elapsed_card.set_values(format_duration(time.perf_counter() - self.started_perf), "Scan in progress")

    def _reset_stage_list(self) -> None:
        self.stage_list.clear()
        self.stage_items.clear()
        for stage in SCAN_STAGES:
            item = QListWidgetItem(f"Waiting - {stage}")
            self.stage_list.addItem(item)
            self.stage_items[stage] = item

    def _activate_stage(self, stage: str) -> None:
        if stage not in self.stage_items:
            return
        index = SCAN_STAGES.index(stage)
        for completed_stage in SCAN_STAGES[:index]:
            self.stage_items[completed_stage].setText(f"Complete - {completed_stage}")
        self.stage_items[stage].setText(f"Scanning - {stage}")
        self.current_stage_index = index

    def _mark_current_stage(self, state: str) -> None:
        if 0 <= self.current_stage_index < len(SCAN_STAGES):
            stage = SCAN_STAGES[self.current_stage_index]
            self.stage_items[stage].setText(f"{state} - {stage}")

    def _complete_all_stages(self) -> None:
        for stage in SCAN_STAGES:
            self.stage_items[stage].setText(f"Complete - {stage}")

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None

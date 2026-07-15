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

from app.models import ScanMode, ScanResult
from app.services.report_service import ReportService
from app.services.scan_service import ScanService
from app.services.settings_service import SettingsService
from app.ui.icons import icon
from app.ui.widgets import Card, SegmentedControl, StatCard, page_header
from app.utils.formatting import format_bytes, format_duration


QUICK_SCAN_STAGES = [
    "User temporary files",
    "Browser cache",
    "Thumbnail cache",
    "App cache",
]

DEEP_SCAN_STAGES = [
    *QUICK_SCAN_STAGES,
    "Downloads review",
    "Large files",
    "Duplicate candidates",
]


class ScanWorker(QObject):
    progress = Signal(str, int, int, int)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        scan_service: ScanService,
        report_service: ReportService,
        scan_mode: ScanMode,
        cancel_event: Event,
    ) -> None:
        super().__init__()
        self.scan_service = scan_service
        self.report_service = report_service
        self.scan_mode = scan_mode
        self.cancel_event = cancel_event

    def run(self) -> None:
        try:
            result = self.scan_service.scan(
                self.scan_mode,
                self.progress.emit,
                self.cancel_event,
            )
        except Exception as exc:  # pragma: no cover - UI safety net
            self.failed.emit(str(exc))
            return
        try:
            self.report_service.save_scan(result)
        except Exception as exc:
            result.errors.append(f"Scan history could not be saved: {exc}")
        self.completed.emit(result)


class ScanPage(QWidget):
    scan_completed = Signal(object)

    def __init__(
        self,
        scan_service: ScanService,
        report_service: ReportService,
        settings_service: SettingsService,
    ) -> None:
        super().__init__()
        self.scan_service = scan_service
        self.report_service = report_service
        self.settings_service = settings_service
        self.thread: QThread | None = None
        self.worker: ScanWorker | None = None
        self.cancel_event = Event()
        self.started_perf = 0.0
        self.stage_items: dict[str, QListWidgetItem] = {}
        self.stage_totals: dict[str, tuple[int, int]] = {}
        self.active_stages: list[str] = []
        self.current_stage_index = -1

        saved_mode = self.settings_service.get_scan_mode()
        self.mode_control = SegmentedControl([ScanMode.QUICK.value, ScanMode.DEEP.value], saved_mode)
        self.mode_control.value_changed.connect(self.on_mode_changed)
        self.mode_description = QLabel()
        self.mode_description.setObjectName("MutedText")
        self.mode_description.setWordWrap(True)

        self.status_label = QLabel("Ready to scan local user-level cleanup locations.")
        self.status_label.setObjectName("MutedText")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)

        self.elapsed_card = StatCard("Elapsed", "0 sec", "No scan running")
        self.files_card = StatCard("Findings", "0", "Items found so far")
        self.space_card = StatCard("Space Found", "0 B", "Safe and review findings")

        self.stage_list = QListWidget()
        self.stage_list.setObjectName("SettingsList")
        self.stage_list.setMinimumHeight(250)
        self._reset_stage_list()

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(110)
        self.log.hide()

        self.start_button = QPushButton()
        self.cancel_button = QPushButton("Cancel Scan")
        self.cancel_button.setProperty("class", "Secondary")
        self.cancel_button.setEnabled(False)
        self.start_button.setIcon(icon("play", "#ffffff"))
        self.cancel_button.setIcon(icon("circle-x", "#4f7fe8"))

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
        mode_row = QHBoxLayout()
        mode_row.addWidget(self.mode_control)
        mode_row.addStretch()
        card_layout.addLayout(mode_row)
        card_layout.addWidget(self.mode_description)
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
        self.on_mode_changed(saved_mode)

    def start_scan(self) -> None:
        if self.thread is not None:
            self.status_label.setText("A scan is already running.")
            return

        self.cancel_event = Event()
        self.thread = QThread()
        scan_mode = ScanMode(self.mode_control.value())
        self.worker = ScanWorker(
            self.scan_service,
            self.report_service,
            scan_mode,
            self.cancel_event,
        )
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.progress.connect(self.on_progress)
        self.worker.completed.connect(self.on_completed)
        self.worker.failed.connect(self.on_failed)
        self.worker.completed.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.worker.deleteLater)
        self.thread.finished.connect(self._clear_thread)

        self.started_perf = time.perf_counter()
        self.current_stage_index = -1
        self.progress_bar.setValue(0)
        self.log.clear()
        self.log.hide()
        self.stage_totals.clear()
        self._reset_stage_list()
        self.start_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        self.mode_control.setEnabled(False)
        self.status_label.setText(f"Starting {scan_mode.value.lower()} scan...")
        self.elapsed_card.set_values("0 sec", "Scan in progress")
        self.files_card.set_values("0", "Items found so far")
        self.space_card.set_values("0 B", "Safe and review findings")
        self.timer.start()
        self.thread.start()

    def cancel_scan(self) -> None:
        if self.thread is None:
            return
        self.cancel_event.set()
        self.cancel_button.setEnabled(False)
        self.status_label.setText("Cancelling scan safely...")
        self._mark_current_stage("Cancelling")

    def on_progress(self, category: str, file_count: int, bytes_found: int, progress: int) -> None:
        self.progress_bar.setValue(min(progress, 99))
        self.status_label.setText(f"{category}: {file_count} item(s), {format_bytes(bytes_found)} found")
        self.stage_totals[category] = (file_count, bytes_found)
        total_files = sum(count for count, _ in self.stage_totals.values())
        total_bytes = sum(size for _, size in self.stage_totals.values())
        self.files_card.set_values(f"{total_files:,}", f"Current stage: {category}")
        self.space_card.set_values(format_bytes(total_bytes), "Findings across completed stages")
        self._activate_stage(category)

    def on_completed(self, result: ScanResult) -> None:
        self.timer.stop()
        self.progress_bar.setValue(100)
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.mode_control.setEnabled(True)
        if result.canceled:
            self.status_label.setText("Scan cancelled. Partial results were saved safely.")
            self._mark_current_stage("Cancelled")
        else:
            self.status_label.setText("Scan complete.")
            self._complete_all_stages()

        self.elapsed_card.set_values(format_duration(result.duration_seconds), "Total scan duration")
        self.files_card.set_values(f"{result.total_files_scanned:,}", "Total findings")
        self.space_card.set_values(
            format_bytes(result.safe_bytes + result.review_bytes),
            "Safe and review space found",
        )
        for error in result.errors[:10]:
            self.log.append(error)
        self.log.append(
            f"Found {format_bytes(result.safe_bytes)} safe to clean and {format_bytes(result.review_bytes)} for review."
        )
        self.log.show()
        self.scan_completed.emit(result)

    def on_failed(self, message: str) -> None:
        self.timer.stop()
        self.start_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.mode_control.setEnabled(True)
        self.status_label.setText("Scan could not complete.")
        self._mark_current_stage("Error")
        self.log.append(message)
        self.log.show()

    def update_elapsed(self) -> None:
        if self.started_perf <= 0:
            return
        self.elapsed_card.set_values(format_duration(time.perf_counter() - self.started_perf), "Scan in progress")

    def _reset_stage_list(self) -> None:
        self.stage_list.clear()
        self.stage_items.clear()
        self.active_stages = (
            DEEP_SCAN_STAGES
            if self.mode_control.value() == ScanMode.DEEP.value
            else QUICK_SCAN_STAGES
        )
        for stage in self.active_stages:
            item = QListWidgetItem(f"Waiting - {stage}")
            self.stage_list.addItem(item)
            self.stage_items[stage] = item

    def _activate_stage(self, stage: str) -> None:
        if stage not in self.stage_items:
            return
        index = self.active_stages.index(stage)
        for completed_stage in self.active_stages[:index]:
            self.stage_items[completed_stage].setText(f"Complete - {completed_stage}")
        self.stage_items[stage].setText(f"Scanning - {stage}")
        self.current_stage_index = index

    def _mark_current_stage(self, state: str) -> None:
        if 0 <= self.current_stage_index < len(self.active_stages):
            stage = self.active_stages[self.current_stage_index]
            self.stage_items[stage].setText(f"{state} - {stage}")

    def _complete_all_stages(self) -> None:
        for stage in self.active_stages:
            self.stage_items[stage].setText(f"Complete - {stage}")

    def _clear_thread(self) -> None:
        self.thread = None
        self.worker = None

    def on_mode_changed(self, mode: str) -> None:
        self.settings_service.set_scan_mode(mode)
        is_deep = mode == ScanMode.DEEP.value
        self.start_button.setText("Start Deep Scan" if is_deep else "Start Quick Scan")
        self.mode_description.setText(
            "Includes personal-folder large-file analysis and duplicate hashing. This may take several minutes."
            if is_deep
            else "Scans user temp files and known browser, thumbnail, and app caches."
        )
        if self.thread is None:
            self.current_stage_index = -1
            self._reset_stage_list()

    def has_active_operation(self) -> bool:
        return self.thread is not None

    def cancel_active_operation(self) -> None:
        if self.thread is not None:
            self.cancel_scan()

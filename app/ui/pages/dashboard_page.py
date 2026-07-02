from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtWidgets import QGridLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from app.models import AiRecommendation, ScanHistoryItem, ScanResult
from app.services.ai_advisor_service import AiAdvisorService
from app.services.report_service import ReportService
from app.services.scan_service import ScanService
from app.ui.widgets import Card, StatCard, page_header
from app.utils.formatting import format_bytes, format_datetime, format_duration


class AiAdvisorWorker(QObject):
    completed = Signal(object)

    def __init__(self, ai_service: AiAdvisorService, scan_result: ScanResult) -> None:
        super().__init__()
        self.ai_service = ai_service
        self.scan_result = scan_result

    def run(self) -> None:
        self.completed.emit(self.ai_service.generate_recommendations(self.scan_result))


class DashboardPage(QWidget):
    def __init__(
        self,
        scan_service: ScanService,
        report_service: ReportService,
        ai_service: AiAdvisorService,
    ) -> None:
        super().__init__()
        self.scan_service = scan_service
        self.report_service = report_service
        self.ai_service = ai_service
        self.current_scan: ScanResult | None = None
        self.ai_thread: QThread | None = None
        self.ai_worker: AiAdvisorWorker | None = None

        self.storage_card = StatCard("Storage Overview")
        self.safe_card = StatCard("Safe To Clean")
        self.review_card = StatCard("Needs Review")
        self.last_scan_card = StatCard("Last Scan")

        self.ai_label = QTextEdit()
        self.ai_label.setReadOnly(True)
        self.ai_label.setMinimumHeight(155)
        self.ai_label.setPlainText("Run a scan to generate AI cleanup advice.")
        self.generate_ai_button = QPushButton("Generate AI Advice")
        self.generate_ai_button.setProperty("class", "Secondary")
        self.generate_ai_button.setEnabled(False)
        self.generate_ai_button.clicked.connect(self.generate_ai_advice)
        ai_card = Card()
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(18, 16, 18, 16)
        ai_title = QLabel("AI Cleanup Advisor")
        ai_title.setProperty("class", "CardTitle")
        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(self.ai_label)
        ai_layout.addWidget(self.generate_ai_button)

        self.start_scan_button = QPushButton("Start Quick Scan")
        self.view_results_button = QPushButton("View Results")
        self.clean_safe_button = QPushButton("Clean Safe Items")
        self.view_latest_report_button = QPushButton("View Latest Report")
        self.view_results_button.setProperty("class", "Secondary")
        self.clean_safe_button.setProperty("class", "Secondary")
        self.view_latest_report_button.setProperty("class", "Secondary")

        actions_card = Card()
        actions_layout = QVBoxLayout(actions_card)
        actions_layout.setContentsMargins(18, 16, 18, 16)
        actions_title = QLabel("Recommended Action")
        actions_title.setProperty("class", "CardTitle")
        actions_layout.addWidget(actions_title)
        actions_layout.addWidget(self.start_scan_button)
        actions_layout.addWidget(self.view_results_button)
        actions_layout.addWidget(self.clean_safe_button)
        actions_layout.addWidget(self.view_latest_report_button)
        actions_layout.addStretch()

        grid = QGridLayout()
        grid.setSpacing(14)
        grid.addWidget(self.storage_card, 0, 0)
        grid.addWidget(self.safe_card, 0, 1)
        grid.addWidget(self.review_card, 0, 2)
        grid.addWidget(self.last_scan_card, 1, 0)
        grid.addWidget(ai_card, 1, 1)
        grid.addWidget(actions_card, 1, 2)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(2, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 22, 24, 22)
        layout.addWidget(page_header("Dashboard", "Local disk cleanup overview and scan status."))
        layout.addLayout(grid)
        layout.addStretch()
        self.refresh_disk_usage()
        self.load_persisted_summary()

    def refresh_disk_usage(self) -> None:
        usage = self.scan_service.get_disk_usage()
        self.storage_card.set_values(
            format_bytes(int(usage["free"])),
            f"{usage['drive']} free of {format_bytes(int(usage['total']))} ({usage['percent']}% used)",
        )

    def set_scan_result(self, result: ScanResult) -> None:
        self.current_scan = result
        self.safe_card.set_values(format_bytes(result.safe_bytes), f"{result.total_files_scanned} files analyzed")
        self.review_card.set_values(format_bytes(result.review_bytes), "Manual review required")
        self.last_scan_card.set_values(
            format_datetime(result.completed_at),
            f"{format_duration(result.duration_seconds)} - {format_bytes(result.total_bytes_scanned)} found",
        )
        self.ai_label.setPlainText(self.ai_service.generate_scan_summary(result))
        self.generate_ai_button.setEnabled(True)

    def load_persisted_summary(self) -> None:
        latest_scan = self.report_service.latest_scan()
        latest_report = self.report_service.latest_cleanup_report()
        if latest_scan is None:
            self.safe_card.set_values("No scan", "Start a quick scan to calculate safe cleanup")
            self.review_card.set_values("No scan", "Review candidates will appear after scanning")
            self.last_scan_card.set_values("Not scanned yet", "No local scan history found")
            self.ai_label.setPlainText("Run a scan to generate AI cleanup advice.")
            self.generate_ai_button.setEnabled(False)
        else:
            self.set_scan_history(latest_scan)

        if latest_report is not None:
            self.view_latest_report_button.setEnabled(True)
            self.view_latest_report_button.setText(
                f"Latest Report: {format_bytes(latest_report.bytes_recovered)} recovered"
            )
        else:
            self.view_latest_report_button.setText("View Latest Report")
            self.view_latest_report_button.setEnabled(False)

    def set_scan_history(self, scan: ScanHistoryItem) -> None:
        self.safe_card.set_values(format_bytes(scan.safe_bytes), f"{scan.total_files_scanned:,} files analyzed")
        self.review_card.set_values(format_bytes(scan.review_bytes), "Manual review required")
        self.last_scan_card.set_values(
            format_datetime(scan.completed_at),
            f"{format_duration(scan.duration_seconds)} - {format_bytes(scan.total_bytes_scanned)} found",
        )
        self.ai_label.setPlainText(
            f"Latest saved scan found {format_bytes(scan.safe_bytes)} safe to clean and "
            f"{format_bytes(scan.review_bytes)} that needs review. Run a new scan for full AI advice."
        )
        self.generate_ai_button.setEnabled(False)

    def generate_ai_advice(self) -> None:
        if self.current_scan is None or self.ai_thread is not None:
            return
        self.ai_label.setPlainText("Generating AI cleanup advice...")
        self.generate_ai_button.setEnabled(False)
        self.ai_thread = QThread()
        self.ai_worker = AiAdvisorWorker(self.ai_service, self.current_scan)
        self.ai_worker.moveToThread(self.ai_thread)
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.completed.connect(self.on_ai_completed)
        self.ai_worker.completed.connect(self.ai_thread.quit)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        self.ai_thread.finished.connect(self._clear_ai_thread)
        self.ai_thread.start()

    def on_ai_completed(self, recommendation: AiRecommendation) -> None:
        parts = [recommendation.summary]
        if recommendation.recommended_next_steps:
            parts.append("\nRecommended next steps:")
            parts.extend(f"- {step}" for step in recommendation.recommended_next_steps)
        if recommendation.review_priorities:
            parts.append("\nReview priorities:")
            parts.extend(f"- {priority}" for priority in recommendation.review_priorities)
        if recommendation.safety_notes:
            parts.append("\nSafety notes:")
            parts.extend(f"- {note}" for note in recommendation.safety_notes)
        self.ai_label.setPlainText("\n".join(parts))
        self.generate_ai_button.setEnabled(self.current_scan is not None)

    def _clear_ai_thread(self) -> None:
        self.ai_thread = None
        self.ai_worker = None

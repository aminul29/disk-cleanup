from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.models import CleanupReport
from app.services.report_service import ReportService
from app.ui.widgets import Card, page_header
from app.utils.formatting import format_bytes, format_datetime, format_duration


class ReportDetailDialog(QDialog):
    def __init__(self, report: CleanupReport, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.report = report
        self.setWindowTitle("Cleanup Report Details")
        self.resize(720, 520)

        title = QLabel("Cleanup Report")
        title.setObjectName("SectionTitle")
        summary = QLabel(self._summary_text())
        summary.setObjectName("InfoPill")
        summary.setWordWrap(True)

        details = QTextEdit()
        details.setReadOnly(True)
        details.setPlainText(self._detail_text())

        copy_button = QPushButton("Copy Summary")
        copy_button.clicked.connect(self.copy_summary)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        action_row = QHBoxLayout()
        action_row.addWidget(copy_button)
        action_row.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addWidget(details)
        layout.addLayout(action_row)
        layout.addWidget(buttons)

    def copy_summary(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self._detail_text())
        QMessageBox.information(self, "Copied", "Report summary copied to clipboard.")

    def _summary_text(self) -> str:
        return (
            f"Recovered {format_bytes(self.report.bytes_recovered)} from "
            f"{self.report.files_deleted} safe item(s). "
            f"Skipped {self.report.files_skipped} item(s)."
        )

    def _detail_text(self) -> str:
        categories = ", ".join(self.report.categories_cleaned) or "None"
        errors = "\n".join(f"- {error}" for error in self.report.errors) or "None"
        return (
            f"Report ID: {self.report.report_id}\n"
            f"Scan ID: {self.report.scan_id}\n"
            f"Created: {format_datetime(self.report.created_at)}\n"
            f"Recovered: {format_bytes(self.report.bytes_recovered)}\n"
            f"Files cleaned: {self.report.files_deleted}\n"
            f"Files skipped: {self.report.files_skipped}\n"
            f"Categories cleaned: {categories}\n\n"
            f"Errors:\n{errors}\n\n"
            "Safety note: DiskWise cleaned only selected Safe items. Review and Protected items are excluded."
        )


class ReportsPage(QWidget):
    def __init__(self, report_service: ReportService) -> None:
        super().__init__()
        self.report_service = report_service
        self.reports: list[CleanupReport] = []

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setProperty("class", "Secondary")
        self.refresh_button.clicked.connect(self.refresh)

        self.detail_button = QPushButton("View Details")
        self.detail_button.clicked.connect(self.show_selected_report)

        self.cleanup_table = QTableWidget(0, 7)
        self.cleanup_table.setHorizontalHeaderLabels(
            ["Created", "Recovered", "Files Cleaned", "Skipped", "Categories", "Errors", "Summary"]
        )
        self.cleanup_table.setColumnWidth(0, 160)
        self.cleanup_table.setColumnWidth(4, 180)
        self.cleanup_table.setColumnWidth(6, 360)
        self.cleanup_table.itemDoubleClicked.connect(lambda _: self.show_selected_report())

        self.scan_table = QTableWidget(0, 9)
        self.scan_table.setHorizontalHeaderLabels(
            [
                "Started",
                "Duration",
                "Files",
                "Total Found",
                "Safe",
                "Review",
                "Large Files",
                "Duplicates",
                "Errors",
            ]
        )
        self.scan_table.setColumnWidth(0, 160)

        tabs = QTabWidget()
        tabs.addTab(self._table_card(self.cleanup_table), "Cleanup Reports")
        tabs.addTab(self._table_card(self.scan_table), "Scan Sessions")

        actions = QWidget()
        actions_layout = QHBoxLayout(actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.addWidget(self.refresh_button)
        actions_layout.addWidget(self.detail_button)
        actions_layout.addStretch()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)
        layout.addWidget(page_header("Reports", "Review cleanup reports and previous scan sessions stored locally."))
        layout.addWidget(actions)
        layout.addWidget(tabs)
        self.refresh()

    def _table_card(self, table: QTableWidget) -> Card:
        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.addWidget(table)
        return card

    def refresh(self) -> None:
        self.refresh_cleanup_reports()
        self.refresh_scan_history()

    def refresh_cleanup_reports(self) -> None:
        self.reports = self.report_service.list_cleanup_reports()
        self.cleanup_table.setRowCount(len(self.reports))
        for row, report in enumerate(self.reports):
            values = [
                format_datetime(report.created_at),
                format_bytes(report.bytes_recovered),
                str(report.files_deleted),
                str(report.files_skipped),
                ", ".join(report.categories_cleaned),
                str(len(report.errors)),
                report.summary,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, report.report_id)
                self.cleanup_table.setItem(row, column, item)

    def refresh_scan_history(self) -> None:
        scans = self.report_service.list_scan_history()
        self.scan_table.setRowCount(len(scans))
        for row, scan in enumerate(scans):
            total_found = scan.safe_bytes + scan.review_bytes + scan.protected_bytes
            values = [
                format_datetime(scan.started_at),
                format_duration(scan.duration_seconds),
                f"{scan.total_files_scanned:,}",
                format_bytes(total_found),
                format_bytes(scan.safe_bytes),
                format_bytes(scan.review_bytes),
                str(scan.large_file_count),
                str(scan.duplicate_group_count),
                str(scan.error_count),
            ]
            for column, value in enumerate(values):
                self.scan_table.setItem(row, column, QTableWidgetItem(value))

    def show_selected_report(self) -> None:
        row = self.cleanup_table.currentRow()
        if row < 0 or row >= len(self.reports):
            QMessageBox.information(self, "No Report Selected", "Select a cleanup report first.")
            return
        ReportDetailDialog(self.reports[row], self).exec()

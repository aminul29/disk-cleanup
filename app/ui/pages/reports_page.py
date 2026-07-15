from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHeaderView,
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
from app.ui.icons import icon
from app.ui.widgets import Card, StatCard, page_header
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
            f"Moved {format_bytes(self.report.bytes_recovered)} from "
            f"{self.report.files_deleted} Safe item(s) to the Recycle Bin. "
            f"Skipped {self.report.files_skipped} item(s)."
        )

    def _detail_text(self) -> str:
        categories = (
            ", ".join(
                category.replace("_", " ").title()
                for category in self.report.categories_cleaned
            )
            or "None"
        )
        errors = "\n".join(f"- {error}" for error in self.report.errors) or "None"
        before = (
            format_bytes(self.report.free_space_before_bytes)
            if self.report.free_space_before_bytes
            else "Not recorded"
        )
        after = (
            format_bytes(self.report.free_space_after_bytes)
            if self.report.free_space_after_bytes
            else "Not recorded"
        )
        return (
            f"Report ID: {self.report.report_id}\n"
            f"Scan ID: {self.report.scan_id}\n"
            f"Created: {format_datetime(self.report.created_at)}\n"
            f"Moved to Recycle Bin: {format_bytes(self.report.bytes_recovered)}\n"
            f"Files cleaned: {self.report.files_deleted}\n"
            f"Files skipped: {self.report.files_skipped}\n"
            f"Duration: {format_duration(self.report.duration_seconds)}\n"
            f"Free space before: {before}\n"
            f"Free space after: {after}\n"
            f"Canceled: {'Yes' if self.report.canceled else 'No'}\n"
            f"Categories cleaned: {categories}\n\n"
            f"Errors:\n{errors}\n\n"
            "Safety note: DiskWise cleaned only selected Safe items. Review and Protected items are excluded."
        )


class ReportsPage(QWidget):
    def __init__(self, report_service: ReportService) -> None:
        super().__init__()
        self.report_service = report_service
        self.reports: list[CleanupReport] = []

        self.recovered_card = StatCard("Moved to Recycle Bin", "0 B", "Across local reports")
        self.cleanups_card = StatCard("Cleanups", "0", "Completed cleanup sessions")
        self.latest_card = StatCard("Latest Cleanup", "Not yet", "No cleanup report found")
        self.latest_card.value_label.setProperty("class", "CardValueCompact")

        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.setProperty("class", "Secondary")
        self.refresh_button.clicked.connect(self.refresh)
        self.refresh_button.setIcon(icon("refresh-cw", "#4f7fe8"))

        self.detail_button = QPushButton("View Details")
        self.detail_button.setEnabled(False)
        self.detail_button.clicked.connect(self.show_selected_report)
        self.detail_button.setIcon(icon("file-search", "#ffffff"))

        self.cleanup_table = QTableWidget(0, 7)
        self.cleanup_table.setHorizontalHeaderLabels(
            [
                "Created",
                "Moved",
                "Duration",
                "Files Cleaned",
                "Skipped",
                "Categories",
                "Issues",
            ]
        )
        self._configure_table(self.cleanup_table)
        self.cleanup_table.itemDoubleClicked.connect(lambda _: self.show_selected_report())
        self.cleanup_table.itemSelectionChanged.connect(self._update_detail_button)

        self.scan_table = QTableWidget(0, 11)
        self.scan_table.setHorizontalHeaderLabels(
            [
                "Started",
                "Mode",
                "Status",
                "Duration",
                "Findings",
                "Total Found",
                "Safe",
                "Review",
                "Large Files",
                "Duplicates",
                "Errors",
            ]
        )
        self._configure_table(self.scan_table)

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
        summary_grid = QGridLayout()
        summary_grid.setSpacing(12)
        summary_grid.addWidget(self.recovered_card, 0, 0)
        summary_grid.addWidget(self.cleanups_card, 0, 1)
        summary_grid.addWidget(self.latest_card, 0, 2)
        layout.addLayout(summary_grid)
        layout.addWidget(actions)
        layout.addWidget(tabs, 1)
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
                format_duration(report.duration_seconds),
                str(report.files_deleted),
                str(report.files_skipped),
                f"{len(report.categories_cleaned)} cleaned",
                str(len(report.errors)),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setData(Qt.ItemDataRole.UserRole, report.report_id)
                self.cleanup_table.setItem(row, column, item)
        total_recovered = sum(report.bytes_recovered for report in self.reports)
        self.recovered_card.set_values(
            format_bytes(total_recovered),
            "Across local reports",
        )
        self.cleanups_card.set_values(
            f"{len(self.reports):,}",
            "Completed cleanup sessions",
        )
        if self.reports:
            latest = self.reports[0]
            self.latest_card.set_values(
                format_datetime(latest.created_at),
                f"{format_bytes(latest.bytes_recovered)} moved",
            )
            self.cleanup_table.selectRow(0)
        else:
            self.latest_card.set_values("Not yet", "No cleanup report found")
        self._update_detail_button()

    def refresh_scan_history(self) -> None:
        scans = self.report_service.list_scan_history()
        self.scan_table.setRowCount(len(scans))
        for row, scan in enumerate(scans):
            total_found = scan.safe_bytes + scan.review_bytes + scan.protected_bytes
            values = [
                format_datetime(scan.started_at),
                scan.mode.value,
                "Canceled" if scan.canceled else "Completed",
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

    def _configure_table(self, table: QTableWidget) -> None:
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)

    def _update_detail_button(self) -> None:
        self.detail_button.setEnabled(self.cleanup_table.currentRow() >= 0)

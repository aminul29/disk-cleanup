from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import CleanupItem, ScanResult
from app.ui.widgets import Card, page_header
from app.utils.formatting import format_bytes, format_datetime


class LargeFilesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.current_items: list[CleanupItem] = []

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search file name, path, or type")
        self.search_input.textChanged.connect(self.refresh_table)

        self.filter_combo = QComboBox()
        self.filter_combo.addItems(
            [
                "Larger than 100 MB",
                "Larger than 500 MB",
                "Larger than 1 GB",
                "Older than 90 days",
                "Older than 180 days",
                "Older than 365 days",
            ]
        )
        self.filter_combo.currentIndexChanged.connect(self.refresh_table)

        self.review_banner = QLabel(
            "Large files are Review-only. DiskWise will not delete them in this MVP."
        )
        self.review_banner.setObjectName("InfoPill")

        self.empty_label = QLabel("Run a scan to find large files that may need review.")
        self.empty_label.setObjectName("InfoPill")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Name", "Path", "Size", "Modified", "Type", "Risk", "Reason"])
        self.table.setColumnWidth(0, 220)
        self.table.setColumnWidth(1, 420)
        self.table.setColumnWidth(6, 300)

        filters = QWidget()
        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(10)
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(self.filter_combo)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)
        card_layout.addWidget(self.review_banner)
        card_layout.addWidget(filters)
        card_layout.addWidget(self.empty_label)
        card_layout.addWidget(self.table)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)
        layout.addWidget(page_header("Large Files", "Review storage-heavy files without auto-cleaning them."))
        layout.addWidget(card)
        self.table.hide()

    def set_scan_result(self, result: ScanResult) -> None:
        self.current_items = result.large_files
        self.refresh_table()

    def refresh_table(self) -> None:
        items = self.filtered_items()
        self.table.setRowCount(len(items))
        for row, item in enumerate(items):
            values = [
                item.file_name,
                item.file_path,
                format_bytes(item.size_bytes),
                format_datetime(item.last_modified_at),
                item.extension or "File",
                item.risk_level.value,
                item.reason,
            ]
            for column, value in enumerate(values):
                table_item = QTableWidgetItem(value)
                if column == 5:
                    table_item.setForeground(Qt.GlobalColor.darkYellow)
                self.table.setItem(row, column, table_item)

        has_items = bool(items)
        self.empty_label.setVisible(not has_items)
        self.table.setVisible(has_items)

    def filtered_items(self) -> list[CleanupItem]:
        index = self.filter_combo.currentIndex()
        if index <= 2:
            threshold = [100, 500, 1024][index] * 1024 * 1024
            items = [item for item in self.current_items if item.size_bytes >= threshold]
        else:
            days = [90, 180, 365][index - 3]
            cutoff = datetime.now() - timedelta(days=days)
            items = [
                item
                for item in self.current_items
                if item.last_modified_at is not None and item.last_modified_at < cutoff
            ]

        query = self.search_input.text().strip().lower()
        if not query:
            return items
        return [
            item
            for item in items
            if query in item.file_name.lower()
            or query in item.file_path.lower()
            or query in item.extension.lower()
            or query in item.reason.lower()
        ]

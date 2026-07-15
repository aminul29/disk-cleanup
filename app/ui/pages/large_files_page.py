from __future__ import annotations

from datetime import datetime, timedelta

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import CleanupItem, ScanMode, ScanResult
from app.ui.icons import icon
from app.ui.widgets import Card, page_header
from app.utils.formatting import format_bytes, format_datetime


class LargeFilesPage(QWidget):
    deep_scan_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.current_items: list[CleanupItem] = []
        self.last_scan_mode: ScanMode | None = None

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
            "Large files are Review-only. DiskWise never deletes them automatically."
        )
        self.review_banner.setObjectName("InfoPill")

        self.empty_label = QLabel("Run a scan to find large files that may need review.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setMinimumHeight(120)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.run_deep_button = QPushButton("Run Deep Scan")
        self.run_deep_button.setIcon(icon("scan-search", "#ffffff"))
        self.run_deep_button.clicked.connect(self.deep_scan_requested.emit)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(["Name", "Path", "Size", "Modified", "Type", "Risk", "Reason"])
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for column, width in enumerate([180, 330, 90, 140, 60, 75]):
            self.table.setColumnWidth(column, width)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

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
        card_layout.addWidget(self.run_deep_button, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.table)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)
        layout.addWidget(page_header("Large Files", "Review storage-heavy files without auto-cleaning them."))
        layout.addWidget(card)
        self.table.hide()

    def set_scan_result(self, result: ScanResult) -> None:
        self.current_items = result.large_files
        self.last_scan_mode = result.mode
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
                if column in {1, 6}:
                    table_item.setToolTip(value)
                self.table.setItem(row, column, table_item)

        has_items = bool(items)
        if not has_items:
            if self.current_items:
                self.empty_label.setText("No large files match the current filters.")
            elif self.last_scan_mode == ScanMode.DEEP:
                self.empty_label.setText("The Deep scan did not find large files in supported locations.")
            else:
                self.empty_label.setText("Large-file analysis is included in Deep Scan.")
        self.empty_label.setVisible(not has_items)
        self.run_deep_button.setVisible(not has_items and not self.current_items)
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

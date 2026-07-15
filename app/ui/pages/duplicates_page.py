from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import DuplicateGroup, ScanMode, ScanResult
from app.ui.icons import icon
from app.ui.widgets import Card, page_header
from app.utils.formatting import format_bytes, format_datetime


class DuplicatesPage(QWidget):
    deep_scan_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.current_groups: list[DuplicateGroup] = []
        self.last_scan_mode: ScanMode | None = None

        self.review_banner = QLabel(
            "Duplicate candidates are Review-only. DiskWise suggests what to inspect, not what to delete."
        )
        self.review_banner.setObjectName("InfoPill")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search duplicate file names or locations")
        self.search_input.textChanged.connect(self.refresh_tree)

        self.empty_label = QLabel("Run a scan to find duplicate candidates in Downloads.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setMinimumHeight(120)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.run_deep_button = QPushButton("Run Deep Scan")
        self.run_deep_button.setIcon(icon("scan-search", "#ffffff"))
        self.run_deep_button.clicked.connect(self.deep_scan_requested.emit)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Duplicate Group", "Size", "Modified", "Location"])
        self.tree.setColumnWidth(0, 280)
        self.tree.setColumnWidth(1, 130)
        self.tree.setColumnWidth(3, 560)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setStretchLastSection(True)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)
        card_layout.addWidget(self.review_banner)
        card_layout.addWidget(self.search_input)
        card_layout.addWidget(self.empty_label)
        card_layout.addWidget(self.run_deep_button, alignment=Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(self.tree)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)
        layout.addWidget(page_header("Duplicates", "Inspect duplicate candidates grouped by content hash."))
        layout.addWidget(card)
        self.tree.hide()

    def set_scan_result(self, result: ScanResult) -> None:
        self.current_groups = result.duplicate_groups
        self.last_scan_mode = result.mode
        self.refresh_tree()

    def refresh_tree(self) -> None:
        self.tree.clear()
        query = self.search_input.text().strip().lower()
        groups = [group for group in self.current_groups if self._group_matches(group, query)]

        for group in groups:
            parent = QTreeWidgetItem(
                [
                    f"{len(group.files)} copies - potential savings {format_bytes(group.potential_savings_bytes)}",
                    format_bytes(group.file_size_bytes),
                    "",
                    f"Suggested keep: {group.suggested_keep_file_path}",
                ]
            )
            parent.setForeground(0, Qt.GlobalColor.darkYellow)
            self.tree.addTopLevelItem(parent)
            for item in group.files:
                child = QTreeWidgetItem(
                    [
                        item.file_name,
                        format_bytes(item.size_bytes),
                        format_datetime(item.last_modified_at),
                        item.file_path,
                    ]
                )
                parent.addChild(child)
            parent.setExpanded(True)

        has_groups = bool(groups)
        if not has_groups:
            if self.current_groups:
                self.empty_label.setText("No duplicate groups match the current search.")
            elif self.last_scan_mode == ScanMode.DEEP:
                self.empty_label.setText("The Deep scan did not find duplicate candidates in Downloads.")
            else:
                self.empty_label.setText("Duplicate analysis is included in Deep Scan.")
        self.empty_label.setVisible(not has_groups)
        self.run_deep_button.setVisible(not has_groups and not self.current_groups)
        self.tree.setVisible(has_groups)

    def _group_matches(self, group: DuplicateGroup, query: str) -> bool:
        if not query:
            return True
        if query in group.suggested_keep_file_path.lower():
            return True
        return any(query in item.file_name.lower() or query in item.file_path.lower() for item in group.files)

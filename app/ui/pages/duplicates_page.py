from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from app.models import DuplicateGroup, ScanResult
from app.ui.widgets import Card, page_header
from app.utils.formatting import format_bytes, format_datetime


class DuplicatesPage(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.current_groups: list[DuplicateGroup] = []

        self.review_banner = QLabel(
            "Duplicate candidates are Review-only. DiskWise suggests what to inspect, not what to delete."
        )
        self.review_banner.setObjectName("InfoPill")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search duplicate file names or locations")
        self.search_input.textChanged.connect(self.refresh_tree)

        self.empty_label = QLabel("Run a scan to find duplicate candidates in Downloads.")
        self.empty_label.setObjectName("InfoPill")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Duplicate Group", "Size", "Modified", "Location"])
        self.tree.setColumnWidth(0, 280)
        self.tree.setColumnWidth(1, 130)
        self.tree.setColumnWidth(3, 560)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)
        card_layout.addWidget(self.review_banner)
        card_layout.addWidget(self.search_input)
        card_layout.addWidget(self.empty_label)
        card_layout.addWidget(self.tree)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)
        layout.addWidget(page_header("Duplicates", "Inspect duplicate candidates grouped by content hash."))
        layout.addWidget(card)
        self.tree.hide()

    def set_scan_result(self, result: ScanResult) -> None:
        self.current_groups = result.duplicate_groups
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
        self.empty_label.setVisible(not has_groups)
        self.tree.setVisible(has_groups)

    def _group_matches(self, group: DuplicateGroup, query: str) -> bool:
        if not query:
            return True
        if query in group.suggested_keep_file_path.lower():
            return True
        return any(query in item.file_name.lower() or query in item.file_path.lower() for item in group.files)

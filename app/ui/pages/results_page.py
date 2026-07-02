from __future__ import annotations

from PySide6.QtCore import QObject, QThread, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import AiRecommendation, CleanupCategory, CleanupItem, RiskLevel, ScanResult
from app.services.ai_advisor_service import AiAdvisorService
from app.services.cleanup_service import CleanupService
from app.ui.widgets import Card, StatCard, page_header
from app.utils.formatting import format_bytes, format_datetime


RISK_COLORS = {
    RiskLevel.SAFE: QColor("#166534"),
    RiskLevel.REVIEW: QColor("#92400e"),
    RiskLevel.PROTECTED: QColor("#475569"),
}


class CleanupPreviewDialog(QDialog):
    def __init__(
        self,
        selected_items: list[CleanupItem],
        skipped_review_count: int,
        skipped_protected_count: int,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Cleanup Preview")
        self.setModal(True)
        self.resize(760, 520)

        total_bytes = sum(item.size_bytes for item in selected_items)
        categories = sorted({item.category for item in selected_items})

        title = QLabel("Ready to clean safe items")
        title.setObjectName("SectionTitle")
        description = QLabel(
            "DiskWise will only remove selected Safe items. Review and Protected items are excluded."
        )
        description.setObjectName("SectionDescription")
        description.setWordWrap(True)

        summary = QLabel(
            f"{len(selected_items)} file(s) selected - {format_bytes(total_bytes)} - "
            f"{', '.join(categories) if categories else 'No categories'}"
        )
        summary.setObjectName("InfoPill")

        risk_note = QLabel(
            f"Skipped by safety rules: {skipped_review_count} Review item(s), "
            f"{skipped_protected_count} Protected item(s)."
        )
        risk_note.setObjectName("MutedText")

        table = QTableWidget(min(len(selected_items), 100), 4)
        table.setHorizontalHeaderLabels(["File", "Category", "Size", "Reason"])
        table.setColumnWidth(0, 240)
        table.setColumnWidth(1, 140)
        table.setColumnWidth(2, 110)
        table.setColumnWidth(3, 300)
        for row, item in enumerate(selected_items[:100]):
            values = [
                item.file_name,
                item.category,
                format_bytes(item.size_bytes),
                item.reason,
            ]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))

        self.confirm_checkbox = QCheckBox("I understand that selected safe files will be removed.")
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Cancel | QDialogButtonBox.StandardButton.Ok
        )
        ok_button = self.buttons.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Clean Safe Items")
        ok_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(title)
        layout.addWidget(description)
        layout.addWidget(summary)
        layout.addWidget(risk_note)
        layout.addWidget(table)
        layout.addWidget(self.confirm_checkbox)
        layout.addWidget(self.buttons)

        self.confirm_checkbox.toggled.connect(ok_button.setEnabled)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)


class ResultsAiWorker(QObject):
    completed = Signal(object)

    def __init__(self, ai_service: AiAdvisorService, scan_result: ScanResult) -> None:
        super().__init__()
        self.ai_service = ai_service
        self.scan_result = scan_result

    def run(self) -> None:
        self.completed.emit(self.ai_service.generate_recommendations(self.scan_result))


class ResultsPage(QWidget):
    def __init__(self, cleanup_service: CleanupService, ai_service: AiAdvisorService) -> None:
        super().__init__()
        self.cleanup_service = cleanup_service
        self.ai_service = ai_service
        self.current_scan: ScanResult | None = None
        self.item_lookup: dict[str, CleanupItem] = {}
        self.category_lookup: dict[str, CleanupCategory] = {}
        self._syncing_checks = False
        self.ai_thread: QThread | None = None
        self.ai_worker: ResultsAiWorker | None = None

        self.safe_card = StatCard("Safe To Clean")
        self.review_card = StatCard("Needs Review")
        self.protected_card = StatCard("Protected")

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search categories, files, or reasons")
        self.search_input.textChanged.connect(self.apply_filters)

        self.risk_filter = QComboBox()
        self.risk_filter.addItems(["All risks", "Safe", "Review", "Protected"])
        self.risk_filter.currentIndexChanged.connect(self.apply_filters)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Category or File", "Risk", "Size", "Last Modified", "Reason"])
        self.tree.setColumnWidth(0, 380)
        self.tree.setColumnWidth(1, 110)
        self.tree.setColumnWidth(2, 120)
        self.tree.setColumnWidth(3, 160)
        self.tree.itemChanged.connect(self.on_item_changed)

        self.empty_label = QLabel("Run a scan to see cleanup categories.")
        self.empty_label.setObjectName("InfoPill")
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview_button = QPushButton("Preview Cleanup")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.preview_cleanup)
        self.ai_button = QPushButton("Ask AI To Review This Scan")
        self.ai_button.setProperty("class", "Secondary")
        self.ai_button.setEnabled(False)
        self.ai_button.clicked.connect(self.generate_ai_advice)

        self.ai_summary = QLabel("Run a scan, then ask AI for prioritized cleanup advice.")
        self.ai_summary.setObjectName("InfoPill")
        self.ai_summary.setWordWrap(True)
        self.ai_plan = QLabel("")
        self.ai_plan.setObjectName("SectionDescription")
        self.ai_plan.setWordWrap(True)
        self.ai_review = QLabel("")
        self.ai_review.setObjectName("SectionDescription")
        self.ai_review.setWordWrap(True)
        self.ai_warnings = QLabel("")
        self.ai_warnings.setObjectName("SectionDescription")
        self.ai_warnings.setWordWrap(True)

        ai_card = Card()
        ai_layout = QVBoxLayout(ai_card)
        ai_layout.setContentsMargins(18, 16, 18, 16)
        ai_layout.setSpacing(10)
        ai_title = QLabel("AI Cleanup Advice")
        ai_title.setProperty("class", "CardTitle")
        ai_layout.addWidget(ai_title)
        ai_layout.addWidget(self.ai_summary)
        ai_layout.addWidget(self.ai_plan)
        ai_layout.addWidget(self.ai_review)
        ai_layout.addWidget(self.ai_warnings)
        ai_layout.addWidget(self.ai_button, alignment=Qt.AlignmentFlag.AlignRight)

        filters = QWidget()
        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(10)
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(self.risk_filter)

        card = Card()
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 16, 18, 16)
        card_layout.setSpacing(12)
        card_layout.addWidget(filters)
        card_layout.addWidget(self.empty_label)
        card_layout.addWidget(self.tree)
        card_layout.addWidget(self.preview_button, alignment=Qt.AlignmentFlag.AlignRight)

        summary_grid = QGridLayout()
        summary_grid.setSpacing(14)
        summary_grid.addWidget(self.safe_card, 0, 0)
        summary_grid.addWidget(self.review_card, 0, 1)
        summary_grid.addWidget(self.protected_card, 0, 2)
        summary_grid.setColumnStretch(0, 1)
        summary_grid.setColumnStretch(1, 1)
        summary_grid.setColumnStretch(2, 1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(14)
        layout.addWidget(page_header("Results", "Review findings, select Safe items, and preview cleanup."))
        layout.addLayout(summary_grid)
        layout.addWidget(ai_card)
        layout.addWidget(card)

        self.tree.hide()

    def set_scan_result(self, result: ScanResult) -> None:
        self.current_scan = result
        self.item_lookup.clear()
        self.category_lookup = {category.id: category for category in result.categories}

        self.safe_card.set_values(format_bytes(result.safe_bytes), "Selected by default where safe")
        self.review_card.set_values(format_bytes(result.review_bytes), "Manual review only")
        self.protected_card.set_values(format_bytes(result.protected_bytes), "Never cleaned by DiskWise")

        self.populate_tree(result.categories)
        self.empty_label.setVisible(not result.categories)
        self.tree.setVisible(bool(result.categories))
        self.preview_button.setEnabled(bool(result.categories))
        self.ai_button.setEnabled(bool(result.categories))
        self.ai_summary.setText("AI can prioritize safe cleanup and review-only categories using aggregate scan data.")
        self.ai_plan.clear()
        self.ai_review.clear()
        self.ai_warnings.clear()
        self.apply_filters()

    def populate_tree(self, categories: list[CleanupCategory]) -> None:
        self._syncing_checks = True
        self.tree.clear()
        for category in categories:
            parent = QTreeWidgetItem(
                [
                    f"{category.name} ({category.file_count})",
                    category.risk_level.value,
                    format_bytes(category.total_bytes),
                    "",
                    category.description,
                ]
            )
            parent.setData(0, Qt.ItemDataRole.UserRole, ("category", category.id))
            parent.setFlags(parent.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            parent.setCheckState(
                0,
                Qt.CheckState.Checked
                if category.risk_level == RiskLevel.SAFE and category.is_selected_by_default
                else Qt.CheckState.Unchecked,
            )
            self._style_risk(parent, category.risk_level)
            if category.risk_level != RiskLevel.SAFE:
                parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

            self.tree.addTopLevelItem(parent)
            for item in category.items[:1000]:
                self.item_lookup[item.id] = item
                child = QTreeWidgetItem(
                    [
                        item.file_name,
                        item.risk_level.value,
                        format_bytes(item.size_bytes),
                        format_datetime(item.last_modified_at),
                        item.reason,
                    ]
                )
                child.setData(0, Qt.ItemDataRole.UserRole, ("item", item.id))
                child.setFlags(child.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                child.setCheckState(
                    0,
                    Qt.CheckState.Checked if item.risk_level == RiskLevel.SAFE and item.is_selected else Qt.CheckState.Unchecked,
                )
                self._style_risk(child, item.risk_level)
                if item.risk_level != RiskLevel.SAFE:
                    child.setFlags(child.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)
                parent.addChild(child)
            parent.setExpanded(category.risk_level == RiskLevel.SAFE)
        self._syncing_checks = False

    def on_item_changed(self, changed_item: QTreeWidgetItem, column: int) -> None:
        if self._syncing_checks or column != 0:
            return

        data = changed_item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return

        kind, identifier = data
        self._syncing_checks = True
        if kind == "category":
            category = self.category_lookup.get(identifier)
            if category and category.risk_level == RiskLevel.SAFE:
                state = changed_item.checkState(0)
                for index in range(changed_item.childCount()):
                    child = changed_item.child(index)
                    child_data = child.data(0, Qt.ItemDataRole.UserRole)
                    if child_data and self.item_lookup[child_data[1]].risk_level == RiskLevel.SAFE:
                        child.setCheckState(0, state)
        elif kind == "item":
            parent = changed_item.parent()
            if parent is not None:
                checked = 0
                unchecked = 0
                for index in range(parent.childCount()):
                    child = parent.child(index)
                    if child.checkState(0) == Qt.CheckState.Checked:
                        checked += 1
                    else:
                        unchecked += 1
                if checked and unchecked:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                elif checked:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                else:
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
        self._syncing_checks = False

    def selected_safe_items(self) -> list[CleanupItem]:
        if self.current_scan is None:
            return []

        selected: list[CleanupItem] = []
        for parent_index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(parent_index)
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                if child.checkState(0) != Qt.CheckState.Checked:
                    continue
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if not data:
                    continue
                item = self.item_lookup.get(data[1])
                if item:
                    item.is_selected = True
                    selected.append(item)
        return self.cleanup_service.preview_items(selected)

    def preview_cleanup(self) -> None:
        if self.current_scan is None:
            return

        selected_items = self.selected_safe_items()
        review_count = sum(category.file_count for category in self.current_scan.categories if category.risk_level == RiskLevel.REVIEW)
        protected_count = sum(category.file_count for category in self.current_scan.categories if category.risk_level == RiskLevel.PROTECTED)

        if not selected_items:
            QMessageBox.information(self, "No Safe Items", "No safe cleanup items are selected.")
            return

        dialog = CleanupPreviewDialog(selected_items, review_count, protected_count, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return

        result = self.cleanup_service.cleanup_safe_items(self.current_scan.scan_id, selected_items)
        QMessageBox.information(
            self,
            "Cleanup Complete",
            f"Recovered {format_bytes(result.bytes_recovered)} from {result.files_deleted} file(s).\n"
            f"Skipped: {result.files_skipped}\nErrors: {len(result.errors)}",
        )

    def apply_filters(self) -> None:
        text = self.search_input.text().strip().lower()
        risk = self.risk_filter.currentText()

        for parent_index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(parent_index)
            category_visible = self._matches_filter(parent, text, risk)
            any_child_visible = False
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                visible = self._matches_filter(child, text, risk)
                child.setHidden(not visible)
                any_child_visible = any_child_visible or visible
            parent.setHidden(not (category_visible or any_child_visible))
            if any_child_visible and text:
                parent.setExpanded(True)

    def _matches_filter(self, item: QTreeWidgetItem, text: str, risk: str) -> bool:
        if risk != "All risks" and item.text(1) != risk:
            return False
        if not text:
            return True
        haystack = " ".join(item.text(index).lower() for index in range(item.columnCount()))
        return text in haystack

    def _style_risk(self, item: QTreeWidgetItem, risk: RiskLevel) -> None:
        color = RISK_COLORS[risk]
        item.setForeground(1, color)
        font = item.font(1)
        font.setBold(True)
        item.setFont(1, font)

    def generate_ai_advice(self) -> None:
        if self.current_scan is None or self.ai_thread is not None:
            return
        self.ai_summary.setText("AI is reviewing aggregate scan data...")
        self.ai_button.setEnabled(False)
        self.ai_thread = QThread()
        self.ai_worker = ResultsAiWorker(self.ai_service, self.current_scan)
        self.ai_worker.moveToThread(self.ai_thread)
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.completed.connect(self.on_ai_completed)
        self.ai_worker.completed.connect(self.ai_thread.quit)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        self.ai_thread.finished.connect(self._clear_ai_thread)
        self.ai_thread.start()

    def on_ai_completed(self, recommendation: AiRecommendation) -> None:
        self.ai_summary.setText(f"{recommendation.summary}\nConfidence: {recommendation.confidence}")
        self.ai_plan.setText(self._format_ai_section("Safe cleanup plan", recommendation.safe_cleanup_plan))
        self.ai_review.setText(self._format_ai_section("Review priorities", recommendation.review_priorities))
        warnings = recommendation.warnings or recommendation.safety_notes
        self.ai_warnings.setText(self._format_ai_section("Warnings and safety notes", warnings))
        self.ai_button.setEnabled(self.current_scan is not None)

    def _format_ai_section(self, title: str, items: list[str]) -> str:
        if not items:
            return f"{title}: None."
        return f"{title}:\n" + "\n".join(f"- {item}" for item in items)

    def _clear_ai_thread(self) -> None:
        self.ai_thread = None
        self.ai_worker = None

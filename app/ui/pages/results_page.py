from __future__ import annotations

from threading import Event

from PySide6.QtCore import QObject, QRect, QThread, Qt, QUrl, Signal
from PySide6.QtGui import QColor, QDesktopServices, QFontMetrics
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.models import (
    AiRecommendation,
    CleanupCategory,
    CleanupItem,
    CleanupResult,
    RiskLevel,
    ScanResult,
)
from app.constants import AI_REPORT_URL
from app.services.ai_advisor_service import AiAdvisorService
from app.services.cleanup_service import CleanupService
from app.ui.icons import icon
from app.ui.widgets import Card, StatCard, page_header
from app.utils.formatting import format_bytes, format_datetime


RISK_COLORS = {
    RiskLevel.SAFE: QColor("#15803d"),
    RiskLevel.REVIEW: QColor("#b45309"),
    RiskLevel.PROTECTED: QColor("#64748b"),
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
        self.resize(980, 580)

        total_bytes = sum(item.size_bytes for item in selected_items)
        categories = sorted({item.category for item in selected_items})

        title = QLabel("Ready to move Safe items")
        title.setObjectName("SectionTitle")
        description = QLabel(
            "DiskWise will move only selected Safe items to the Windows Recycle Bin. "
            "Review and Protected items are excluded."
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

        table = QTableWidget(min(len(selected_items), 100), 5)
        table.setHorizontalHeaderLabels(["File", "Location", "Category", "Size", "Why it is Safe"])
        table.setColumnWidth(0, 180)
        table.setColumnWidth(1, 300)
        table.setColumnWidth(2, 130)
        table.setColumnWidth(3, 100)
        table.setColumnWidth(4, 260)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.horizontalHeader().setStretchLastSection(True)
        for row, item in enumerate(selected_items[:100]):
            values = [
                item.file_name,
                item.file_path,
                item.category,
                format_bytes(item.size_bytes),
                item.reason,
            ]
            for column, value in enumerate(values):
                table.setItem(row, column, QTableWidgetItem(value))

        self.confirm_checkbox = QCheckBox(
            "I understand that the selected Safe files will be moved to the Recycle Bin."
        )
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
        if len(selected_items) > 100:
            preview_note = QLabel(
                f"Showing the first 100 of {len(selected_items):,} selected files. "
                "The total above includes every selected Safe item."
            )
            preview_note.setObjectName("MutedText")
            preview_note.setWordWrap(True)
            layout.addWidget(preview_note)
        layout.addWidget(self.confirm_checkbox)
        layout.addWidget(self.buttons)

        self.confirm_checkbox.toggled.connect(ok_button.setEnabled)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)


class ResultsAiWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, ai_service: AiAdvisorService, scan_result: ScanResult) -> None:
        super().__init__()
        self.ai_service = ai_service
        self.scan_result = scan_result

    def run(self) -> None:
        try:
            recommendation = self.ai_service.generate_recommendations(self.scan_result)
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            self.failed.emit(str(exc))
            return
        self.completed.emit(recommendation)


class CleanupWorker(QObject):
    progress = Signal(int, int, str)
    completed = Signal(object)
    failed = Signal(str)

    def __init__(
        self,
        cleanup_service: CleanupService,
        scan_id: str,
        selected_items: list[CleanupItem],
        cancel_event: Event,
    ) -> None:
        super().__init__()
        self.cleanup_service = cleanup_service
        self.scan_id = scan_id
        self.selected_items = selected_items
        self.cancel_event = cancel_event

    def run(self) -> None:
        try:
            result = self.cleanup_service.cleanup_safe_items(
                self.scan_id,
                self.selected_items,
                progress_callback=self.progress.emit,
                cancel_event=self.cancel_event,
            )
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            self.failed.emit(str(exc))
            return
        self.completed.emit(result)


class ResultsPage(QWidget):
    cleanup_completed = Signal(object)

    def __init__(self, cleanup_service: CleanupService, ai_service: AiAdvisorService) -> None:
        super().__init__()
        self.cleanup_service = cleanup_service
        self.ai_service = ai_service
        settings = getattr(self.ai_service, "settings_service", None)
        self.ai_enabled = settings.ai_summary_enabled() if settings is not None else True
        self.current_scan: ScanResult | None = None
        self.item_lookup: dict[str, CleanupItem] = {}
        self.category_lookup: dict[str, CleanupCategory] = {}
        self._syncing_checks = False
        self.ai_thread: QThread | None = None
        self.ai_worker: ResultsAiWorker | None = None
        self.cleanup_thread: QThread | None = None
        self.cleanup_worker: CleanupWorker | None = None
        self.cleanup_progress: QProgressDialog | None = None
        self.cleanup_cancel_event: Event | None = None

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
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tree.itemChanged.connect(self.on_item_changed)

        self.empty_label = QLabel("Run a scan to see cleanup categories.")
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setMinimumHeight(110)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.preview_button = QPushButton("Preview Cleanup")
        self.preview_button.setEnabled(False)
        self.preview_button.clicked.connect(self.preview_cleanup)
        self.preview_button.setIcon(icon("shield-check", "#ffffff"))
        self.ai_button = QPushButton("Ask AI To Review This Scan")
        self.ai_button.setProperty("class", "Secondary")
        self.ai_button.setEnabled(False)
        self.ai_button.clicked.connect(self.generate_ai_advice)
        self.ai_button.setIcon(icon("sparkles", "#4f7fe8"))
        self.report_ai_button = QPushButton("Report AI Output")
        self.report_ai_button.setProperty("class", "Secondary")
        self.report_ai_button.setIcon(icon("message-square-warning", "#4f7fe8"))
        self.report_ai_button.clicked.connect(self.report_ai_output)
        self.report_ai_button.hide()

        self.ai_summary = QLabel("Run a scan, then ask AI for prioritized cleanup advice.")
        self.ai_summary.setObjectName("InfoPill")
        self.ai_summary.setWordWrap(True)
        self.ai_summary.setAlignment(
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
        )
        self.ai_details = QTextEdit()
        self.ai_details.setObjectName("AiDetails")
        self.ai_details.setReadOnly(True)
        self.ai_details.setMinimumHeight(190)
        self.ai_details.setMaximumHeight(190)
        self.ai_details.hide()

        self.ai_card = Card()
        self.ai_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Maximum)
        ai_layout = QVBoxLayout(self.ai_card)
        ai_layout.setContentsMargins(18, 16, 18, 16)
        ai_layout.setSpacing(10)
        ai_title = QLabel("AI Cleanup Advice")
        ai_title.setProperty("class", "CardTitle")
        ai_header = QHBoxLayout()
        ai_header.addWidget(ai_title)
        ai_header.addStretch()
        ai_header.addWidget(self.report_ai_button)
        ai_header.addWidget(self.ai_button)
        ai_layout.addLayout(ai_header)
        ai_layout.addWidget(self.ai_summary)
        ai_layout.addWidget(self.ai_details)

        filters = QWidget()
        filters_layout = QHBoxLayout(filters)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(10)
        filters_layout.addWidget(self.search_input)
        filters_layout.addWidget(self.risk_filter)

        card = Card()
        card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
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
        layout.addWidget(self.ai_card)
        layout.addWidget(card, 1)

        self.tree.hide()

    def set_scan_result(self, result: ScanResult) -> None:
        self.current_scan = result
        self._update_summary_cards()

        self.populate_tree(result.categories)
        self.empty_label.setVisible(not result.categories)
        self.tree.setVisible(bool(result.categories))
        self.preview_button.setEnabled(self._has_safe_items())
        self.ai_button.setEnabled(bool(result.categories) and self.ai_enabled)
        self._set_ai_summary(
            "AI can prioritize safe cleanup and review-only categories using aggregate scan data."
            if self.ai_enabled
            else "AI advice is disabled in Settings."
        )
        self.ai_details.clear()
        self.ai_details.hide()
        self.report_ai_button.hide()
        self.apply_filters()

    def populate_tree(self, categories: list[CleanupCategory]) -> None:
        self._syncing_checks = True
        self.item_lookup.clear()
        self.category_lookup = {category.id: category for category in categories}
        self.tree.clear()
        for category in categories:
            for item in category.items:
                self.item_lookup[item.id] = item
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
            visible_items = category.items[:1000]
            selected_count = sum(item.is_selected for item in category.items)
            if selected_count and selected_count == len(category.items):
                parent_state = Qt.CheckState.Checked
            elif selected_count:
                parent_state = Qt.CheckState.PartiallyChecked
            else:
                parent_state = Qt.CheckState.Unchecked
            parent.setCheckState(0, parent_state)
            self._style_risk(parent, category.risk_level)
            if category.risk_level != RiskLevel.SAFE:
                parent.setFlags(parent.flags() & ~Qt.ItemFlag.ItemIsUserCheckable)

            self.tree.addTopLevelItem(parent)
            for item in category.items[:1000]:
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
            remaining_count = len(category.items) - len(visible_items)
            if remaining_count > 0:
                more_item = QTreeWidgetItem(
                    [
                        f"{remaining_count:,} additional item(s) included in category selection",
                        "",
                        "",
                        "",
                        "Use the category checkbox to include or exclude all items.",
                    ]
                )
                more_item.setFlags(Qt.ItemFlag.ItemIsEnabled)
                more_item.setForeground(0, QColor("#64748b"))
                parent.addChild(more_item)
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
                selected = state == Qt.CheckState.Checked
                for category_item in category.items:
                    if category_item.risk_level == RiskLevel.SAFE:
                        category_item.is_selected = selected
                for index in range(changed_item.childCount()):
                    child = changed_item.child(index)
                    child_data = child.data(0, Qt.ItemDataRole.UserRole)
                    if (
                        child_data
                        and child_data[0] == "item"
                        and self.item_lookup[child_data[1]].risk_level == RiskLevel.SAFE
                    ):
                        child.setCheckState(0, state)
        elif kind == "item":
            model_item = self.item_lookup.get(identifier)
            if model_item is not None:
                model_item.is_selected = changed_item.checkState(0) == Qt.CheckState.Checked
            parent = changed_item.parent()
            if parent is not None:
                parent_data = parent.data(0, Qt.ItemDataRole.UserRole)
                category = self.category_lookup.get(parent_data[1]) if parent_data else None
                total = len(category.items) if category is not None else 0
                checked = (
                    sum(item.is_selected for item in category.items)
                    if category is not None
                    else 0
                )
                if checked and checked < total:
                    parent.setCheckState(0, Qt.CheckState.PartiallyChecked)
                elif checked:
                    parent.setCheckState(0, Qt.CheckState.Checked)
                else:
                    parent.setCheckState(0, Qt.CheckState.Unchecked)
        self._syncing_checks = False

    def selected_safe_items(self) -> list[CleanupItem]:
        if self.current_scan is None:
            return []

        for parent_index in range(self.tree.topLevelItemCount()):
            parent = self.tree.topLevelItem(parent_index)
            for child_index in range(parent.childCount()):
                child = parent.child(child_index)
                data = child.data(0, Qt.ItemDataRole.UserRole)
                if not data or data[0] != "item":
                    continue
                item = self.item_lookup.get(data[1])
                if item:
                    item.is_selected = child.checkState(0) == Qt.CheckState.Checked
        selected = [
            item
            for category in self.current_scan.categories
            for item in category.items
            if item.is_selected
        ]
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

        self.start_cleanup(selected_items)

    def start_cleanup(self, selected_items: list[CleanupItem]) -> None:
        if self.current_scan is None or self.cleanup_thread is not None:
            return

        self.cleanup_cancel_event = Event()
        self.cleanup_progress = QProgressDialog(
            "Preparing safe cleanup...",
            "Cancel",
            0,
            len(selected_items),
            self,
        )
        self.cleanup_progress.setWindowTitle("Cleaning Safe Items")
        self.cleanup_progress.setWindowModality(Qt.WindowModality.WindowModal)
        self.cleanup_progress.setMinimumDuration(0)
        self.cleanup_progress.setAutoClose(False)
        self.cleanup_progress.setAutoReset(False)
        self.cleanup_progress.canceled.connect(self.cancel_cleanup)
        self.cleanup_progress.show()

        self.preview_button.setEnabled(False)
        self.cleanup_thread = QThread()
        self.cleanup_worker = CleanupWorker(
            self.cleanup_service,
            self.current_scan.scan_id,
            selected_items,
            self.cleanup_cancel_event,
        )
        self.cleanup_worker.moveToThread(self.cleanup_thread)
        self.cleanup_thread.started.connect(self.cleanup_worker.run)
        self.cleanup_worker.progress.connect(self.on_cleanup_progress)
        self.cleanup_worker.completed.connect(self.on_cleanup_completed)
        self.cleanup_worker.completed.connect(self.cleanup_thread.quit)
        self.cleanup_worker.failed.connect(self.on_cleanup_failed)
        self.cleanup_worker.failed.connect(self.cleanup_thread.quit)
        self.cleanup_thread.finished.connect(self.cleanup_worker.deleteLater)
        self.cleanup_thread.finished.connect(self.cleanup_thread.deleteLater)
        self.cleanup_thread.finished.connect(self._clear_cleanup_thread)
        self.cleanup_thread.start()

    def cancel_cleanup(self) -> None:
        if self.cleanup_cancel_event is not None:
            self.cleanup_cancel_event.set()
        if self.cleanup_progress is not None:
            self.cleanup_progress.setLabelText("Canceling after the current file...")

    def on_cleanup_progress(self, completed: int, total: int, file_name: str) -> None:
        if self.cleanup_progress is None:
            return
        self.cleanup_progress.setMaximum(total)
        self.cleanup_progress.setValue(completed)
        self.cleanup_progress.setLabelText(
            f"Moving Safe items to the Recycle Bin...\n{completed:,} of {total:,}: {file_name}"
        )

    def on_cleanup_completed(self, result: CleanupResult) -> None:
        self._close_cleanup_progress()
        self.apply_cleanup_result(result)
        self.cleanup_completed.emit(result)

        message = (
            f"Moved {format_bytes(result.bytes_recovered)} from "
            f"{result.files_deleted:,} file(s) to the Recycle Bin.\n"
            f"Skipped: {result.files_skipped:,}"
        )
        if result.files_deleted:
            message += "\n\nWindows reclaims this space after the Recycle Bin is emptied."
        if result.errors:
            message += (
                f"\n\n{len(result.errors):,} issue(s) were recorded. Files that are open or "
                "locked by Windows remain available for a later scan.\n\n"
                "First issues:\n"
                + "\n".join(f"- {error[:240]}" for error in result.errors[:3])
            )
            if len(result.errors) > 3:
                message += "\n- Open Reports to review the complete issue list."

        if result.canceled:
            QMessageBox.information(self, "Cleanup Canceled", message)
        elif result.files_deleted:
            QMessageBox.information(self, "Cleanup Finished", message)
        else:
            QMessageBox.warning(self, "Nothing Was Cleaned", message)

    def on_cleanup_failed(self, error: str) -> None:
        self._close_cleanup_progress()
        QMessageBox.critical(
            self,
            "Cleanup Failed",
            "DiskWise could not finish cleanup. No Review or Protected items were touched.\n\n"
            f"{error}",
        )

    def apply_cleanup_result(self, result: CleanupResult) -> None:
        if self.current_scan is None:
            return

        deleted_ids = set(result.deleted_item_ids)
        skipped_ids = set(result.skipped_item_ids)
        for category in self.current_scan.categories:
            remaining_items: list[CleanupItem] = []
            for item in category.items:
                if item.id in deleted_ids:
                    continue
                if item.id in skipped_ids:
                    item.is_selected = False
                remaining_items.append(item)
            category.items = remaining_items
            category.file_count = len(remaining_items)
            category.total_bytes = sum(item.size_bytes for item in remaining_items)

        self.current_scan.total_files_scanned = sum(
            category.file_count for category in self.current_scan.categories
        )
        self.current_scan.total_bytes_scanned = sum(
            category.total_bytes for category in self.current_scan.categories
        )
        self.current_scan.safe_bytes = sum(
            category.total_bytes
            for category in self.current_scan.categories
            if category.risk_level == RiskLevel.SAFE
        )
        self.current_scan.review_bytes = sum(
            category.total_bytes
            for category in self.current_scan.categories
            if category.risk_level == RiskLevel.REVIEW
        )
        self.current_scan.protected_bytes = sum(
            category.total_bytes
            for category in self.current_scan.categories
            if category.risk_level == RiskLevel.PROTECTED
        )

        self._update_summary_cards()
        self.populate_tree(self.current_scan.categories)
        self.empty_label.setVisible(not self.current_scan.categories)
        self.tree.setVisible(bool(self.current_scan.categories))
        self.preview_button.setEnabled(self._has_safe_items())
        self._set_ai_summary(
            "Cleanup updated this scan. Ask AI again for advice based on the remaining items."
            if self.ai_enabled
            else "AI advice is disabled in Settings."
        )
        self.ai_details.clear()
        self.ai_details.hide()
        self.report_ai_button.hide()
        self.apply_filters()

    def _update_summary_cards(self) -> None:
        if self.current_scan is None:
            return
        safe_note = (
            "Selected by default where safe"
            if self.current_scan.safe_bytes
            else "No Safe items remain"
        )
        self.safe_card.set_values(format_bytes(self.current_scan.safe_bytes), safe_note)
        self.review_card.set_values(
            format_bytes(self.current_scan.review_bytes),
            "Manual review only",
        )
        self.protected_card.set_values(
            format_bytes(self.current_scan.protected_bytes),
            "Never cleaned by DiskWise",
        )

    def _has_safe_items(self) -> bool:
        if self.current_scan is None:
            return False
        return any(
            item.can_delete and item.risk_level == RiskLevel.SAFE
            for category in self.current_scan.categories
            for item in category.items
        )

    def _close_cleanup_progress(self) -> None:
        if self.cleanup_progress is not None:
            self.cleanup_progress.close()
            self.cleanup_progress.deleteLater()
            self.cleanup_progress = None

    def _clear_cleanup_thread(self) -> None:
        self.cleanup_thread = None
        self.cleanup_worker = None
        self.cleanup_cancel_event = None
        self.preview_button.setEnabled(self._has_safe_items())

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
        self._set_ai_summary("AI is reviewing aggregate scan data...")
        self.ai_button.setEnabled(False)
        self.ai_thread = QThread()
        self.ai_worker = ResultsAiWorker(self.ai_service, self.current_scan)
        self.ai_worker.moveToThread(self.ai_thread)
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.completed.connect(self.on_ai_completed)
        self.ai_worker.completed.connect(self.ai_thread.quit)
        self.ai_worker.failed.connect(self.on_ai_failed)
        self.ai_worker.failed.connect(self.ai_thread.quit)
        self.ai_thread.finished.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        self.ai_thread.finished.connect(self._clear_ai_thread)
        self.ai_thread.start()

    def on_ai_completed(self, recommendation: AiRecommendation) -> None:
        self._set_ai_summary(
            f"{recommendation.summary}\nConfidence: {recommendation.confidence}"
        )
        warnings = recommendation.warnings or recommendation.safety_notes
        sections = [
            self._format_ai_section("Safe cleanup plan", recommendation.safe_cleanup_plan),
            self._format_ai_section("Warnings and safety notes", warnings),
            self._format_ai_section("Review priorities", recommendation.review_priorities),
        ]
        self.ai_details.setPlainText("\n".join(section for section in sections if section))
        self.ai_details.show()
        self.ai_card.layout().activate()
        self.ai_card.updateGeometry()
        self.report_ai_button.show()
        self.ai_button.setEnabled(self.ai_enabled and self.current_scan is not None)

    def on_ai_failed(self, message: str) -> None:
        self._set_ai_summary(f"AI advice could not be generated: {message}")
        self.ai_details.clear()
        self.ai_details.hide()
        self.ai_button.setEnabled(self.ai_enabled and self.current_scan is not None)

    def report_ai_output(self) -> None:
        QDesktopServices.openUrl(QUrl(AI_REPORT_URL))

    def _format_ai_section(self, title: str, items: list[str]) -> str:
        if not items:
            return ""
        return f"{title}:\n" + "\n".join(f"- {item}" for item in items)

    def _set_ai_summary(self, text: str) -> None:
        self.ai_summary.setText(text)
        width = max(self.ai_summary.width() - 24, 480)
        text_height = QFontMetrics(self.ai_summary.font()).boundingRect(
            QRect(0, 0, width, 200),
            Qt.TextFlag.TextWordWrap,
            text,
        ).height()
        self.ai_summary.setFixedHeight(
            min(max(text_height + 22, 42), 82)
        )
        self.ai_summary.updateGeometry()

    def _clear_ai_thread(self) -> None:
        self.ai_thread = None
        self.ai_worker = None

    def set_ai_enabled(self, enabled: bool) -> None:
        self.ai_enabled = enabled
        self.ai_button.setEnabled(
            enabled and self.current_scan is not None and bool(self.current_scan.categories)
        )
        if not enabled:
            self._set_ai_summary("AI advice is disabled in Settings.")
        elif self.current_scan is not None:
            self._set_ai_summary(
                "AI can prioritize safe cleanup and review-only categories using aggregate scan data."
            )

    def has_active_operations(self) -> bool:
        return self.cleanup_thread is not None or self.ai_thread is not None

    def cancel_active_operations(self) -> None:
        if self.cleanup_thread is not None:
            self.cancel_cleanup()

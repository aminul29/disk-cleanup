from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QThread, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.constants import APP_VERSION, PRIVACY_POLICY_URL, SUPPORT_URL
from app.services.ai_advisor_service import AiAdvisorService
from app.services.license_service import MockLicenseService
from app.services.settings_service import SettingsService
from app.ui.styles import apply_app_style
from app.ui.icons import icon
from app.ui.pricing_dialog import PricingDialog
from app.ui.widgets import Card, page_header


class AiConnectionWorker(QObject):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, settings_service: SettingsService) -> None:
        super().__init__()
        self.settings_service = settings_service

    def run(self) -> None:
        try:
            recommendation = AiAdvisorService(self.settings_service).test_connection()
        except Exception as exc:  # pragma: no cover - defensive worker boundary
            self.failed.emit(str(exc))
            return
        self.completed.emit(recommendation)


class SettingsPage(QWidget):
    history_changed = Signal()
    scan_mode_changed = Signal(str)
    ai_enabled_changed = Signal(bool)
    onboarding_requested = Signal()

    def __init__(self, settings_service: SettingsService, license_service: MockLicenseService) -> None:
        super().__init__()
        self.settings_service = settings_service
        self.license_service = license_service
        self.ai_thread: QThread | None = None
        self.ai_worker: AiConnectionWorker | None = None

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["System", "Light", "Dark"])
        self.theme_combo.setCurrentText(self.settings_service.get_theme())
        self.theme_combo.setFixedWidth(220)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)

        self.scan_mode_combo = QComboBox()
        self.scan_mode_combo.addItems(["Quick", "Deep"])
        self.scan_mode_combo.setCurrentText(self.settings_service.get_scan_mode())
        self.scan_mode_combo.setFixedWidth(220)
        self.scan_mode_combo.currentTextChanged.connect(self.on_scan_mode_changed)

        self.privacy_checkbox = QCheckBox("Strict local mode (blocks external AI)")
        self.privacy_checkbox.setChecked(self.settings_service.privacy_mode_enabled())
        self.privacy_checkbox.toggled.connect(self.on_privacy_mode_changed)

        self.ai_checkbox = QCheckBox("AI advice enabled")
        self.ai_checkbox.setChecked(self.settings_service.ai_summary_enabled())
        self.ai_checkbox.toggled.connect(self.on_ai_enabled_changed)

        self.ai_provider_combo = QComboBox()
        self.ai_provider_combo.addItems(["Mock", "OpenRouter"])
        self.ai_provider_combo.setCurrentText(self.settings_service.get_ai_provider())
        self.ai_provider_combo.currentTextChanged.connect(self.on_ai_provider_changed)

        self.openrouter_model_input = QLineEdit()
        self.openrouter_model_input.setText(self.settings_service.get_openrouter_model())
        self.openrouter_model_input.setPlaceholderText("openai/gpt-4.1-mini")

        self.openrouter_key_input = QLineEdit()
        self.openrouter_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.openrouter_key_input.setText(self.settings_service.get_openrouter_api_key())
        self.openrouter_key_input.setPlaceholderText("OpenRouter API key or use OPENROUTER_API_KEY")
        self.openrouter_key_input.setClearButtonEnabled(True)

        self.show_key_checkbox = QCheckBox("Show key")
        self.show_key_checkbox.toggled.connect(
            lambda shown: self.openrouter_key_input.setEchoMode(
                QLineEdit.EchoMode.Normal if shown else QLineEdit.EchoMode.Password
            )
        )

        self.ai_status_label = QLabel("API keys are encrypted for this Windows account.")
        self.ai_status_label.setObjectName("MutedText")

        self.exclusions_list = QListWidget()
        self.exclusions_list.setObjectName("SettingsList")
        self.exclusions_list.setMinimumHeight(160)

        self.add_exclusion_button = QPushButton("Add Folder")
        self.remove_exclusion_button = QPushButton("Remove Selected")
        self.clear_scans_button = QPushButton("Clear Scan History")
        self.clear_reports_button = QPushButton("Clear Cleanup Reports")
        self.clear_logs_button = QPushButton("Clear Diagnostic Logs")
        self.clear_history_button = QPushButton("Clear All History")
        self.reset_settings_button = QPushButton("Reset Settings")
        self.show_welcome_button = QPushButton("Show Welcome")
        self.privacy_policy_button = QPushButton("Privacy Policy")
        self.support_button = QPushButton("Support")
        self.upgrade_button = QPushButton("Preview Roadmap")
        self.save_ai_button = QPushButton("Save AI Settings")
        self.test_ai_button = QPushButton("Test OpenRouter")
        self.remove_exclusion_button.setProperty("class", "Secondary")
        self.clear_scans_button.setProperty("class", "Secondary")
        self.clear_reports_button.setProperty("class", "Secondary")
        self.clear_logs_button.setProperty("class", "Secondary")
        self.clear_history_button.setProperty("class", "Danger")
        self.reset_settings_button.setProperty("class", "Secondary")
        self.show_welcome_button.setProperty("class", "Secondary")
        self.privacy_policy_button.setProperty("class", "Secondary")
        self.support_button.setProperty("class", "Secondary")
        self.upgrade_button.setProperty("class", "Secondary")
        self.test_ai_button.setProperty("class", "Secondary")
        self.add_exclusion_button.setIcon(icon("folder-plus", "#ffffff"))
        self.remove_exclusion_button.setIcon(icon("folder-minus", "#4f7fe8"))
        self.clear_scans_button.setIcon(icon("history", "#4f7fe8"))
        self.clear_reports_button.setIcon(icon("file-x", "#4f7fe8"))
        self.clear_logs_button.setIcon(icon("file-text", "#4f7fe8"))
        self.clear_history_button.setIcon(icon("trash-2", "#ffffff"))
        self.reset_settings_button.setIcon(icon("rotate-ccw", "#4f7fe8"))
        self.show_welcome_button.setIcon(icon("book-open", "#4f7fe8"))
        self.privacy_policy_button.setIcon(icon("shield", "#4f7fe8"))
        self.support_button.setIcon(icon("life-buoy", "#4f7fe8"))
        self.upgrade_button.setIcon(icon("sparkles", "#4f7fe8"))
        self.save_ai_button.setIcon(icon("save", "#ffffff"))
        self.test_ai_button.setIcon(icon("plug-zap", "#4f7fe8"))

        for button in (
            self.add_exclusion_button,
            self.remove_exclusion_button,
            self.clear_scans_button,
            self.clear_reports_button,
            self.clear_logs_button,
            self.clear_history_button,
            self.reset_settings_button,
            self.show_welcome_button,
            self.privacy_policy_button,
            self.support_button,
            self.upgrade_button,
            self.save_ai_button,
            self.test_ai_button,
        ):
            button.setMinimumWidth(150)
            button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.add_exclusion_button.clicked.connect(self.add_exclusion)
        self.remove_exclusion_button.clicked.connect(self.remove_exclusion)
        self.clear_scans_button.clicked.connect(self.clear_scan_history)
        self.clear_reports_button.clicked.connect(self.clear_cleanup_reports)
        self.clear_logs_button.clicked.connect(self.clear_diagnostic_logs)
        self.clear_history_button.clicked.connect(self.clear_history)
        self.reset_settings_button.clicked.connect(self.reset_settings)
        self.show_welcome_button.clicked.connect(self.onboarding_requested.emit)
        self.privacy_policy_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(PRIVACY_POLICY_URL))
        )
        self.support_button.clicked.connect(
            lambda: QDesktopServices.openUrl(QUrl(SUPPORT_URL))
        )
        self.upgrade_button.clicked.connect(self.show_pricing_dialog)
        self.save_ai_button.clicked.connect(self.save_ai_settings)
        self.test_ai_button.clicked.connect(self.test_ai_settings)
        self.on_ai_provider_changed(self.ai_provider_combo.currentText())

        grid = QGridLayout()
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)
        grid.addWidget(self._build_appearance_card(), 0, 0)
        grid.addWidget(self._build_privacy_card(), 0, 1)
        grid.addWidget(self._build_ai_card(), 1, 0, 1, 2)
        grid.addWidget(self._build_exclusions_card(), 2, 0, 1, 2)
        grid.addWidget(self._build_data_card(), 3, 0)
        grid.addWidget(self._build_pro_card(), 3, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        content_layout.addLayout(grid)
        content_layout.addStretch()

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll_area.setWidget(content)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 28, 30, 28)
        layout.setSpacing(10)
        layout.addWidget(page_header("Settings", "Control appearance, scanning, privacy, exclusions, and local data."))
        layout.addWidget(scroll_area)
        self.refresh_exclusions()

    def _build_appearance_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(self._section_title("Appearance"))
        layout.addWidget(self._section_description("Choose how DiskWise should look on this device."))

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 0)
        theme_label = QLabel("Theme")
        theme_label.setObjectName("MutedText")
        row_layout.addWidget(theme_label)
        row_layout.addStretch()
        row_layout.addWidget(self.theme_combo)
        layout.addWidget(row)

        scan_row = QWidget()
        scan_row_layout = QHBoxLayout(scan_row)
        scan_row_layout.setContentsMargins(0, 4, 0, 0)
        scan_label = QLabel("Default scan")
        scan_label.setObjectName("MutedText")
        scan_row_layout.addWidget(scan_label)
        scan_row_layout.addStretch()
        scan_row_layout.addWidget(self.scan_mode_combo)
        layout.addWidget(scan_row)

        version = QLabel(f"Version {APP_VERSION}")
        version.setObjectName("InfoPill")
        layout.addStretch()
        layout.addWidget(version)
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self.reset_settings_button)
        actions.addWidget(self.show_welcome_button)
        actions.addStretch()
        layout.addLayout(actions)
        return card

    def _build_privacy_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(10)
        layout.addWidget(self._section_title("Privacy & AI"))
        layout.addWidget(
            self._section_description(
                "Strict local mode prevents all external AI requests. Scanning and cleanup always stay local."
            )
        )
        layout.addWidget(self.privacy_checkbox)
        local_only = QLabel("No diagnostic telemetry or file details are uploaded.")
        local_only.setObjectName("InfoPill")
        local_only.setWordWrap(True)
        layout.addWidget(local_only)
        layout.addStretch()
        actions = QHBoxLayout()
        actions.setSpacing(10)
        actions.addWidget(self.privacy_policy_button)
        actions.addWidget(self.support_button)
        actions.addStretch()
        layout.addLayout(actions)
        return card

    def _build_ai_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(14)
        layout.addWidget(self._section_title("AI Advisor"))
        layout.addWidget(
            self._section_description(
                "OpenRouter receives aggregate scan totals and category summaries only. "
                "DiskWise does not send file names, paths, or contents."
            )
        )

        top_row = QHBoxLayout()
        top_row.setSpacing(12)
        top_row.addWidget(self._field_group("Provider", self.ai_provider_combo), 1)
        top_row.addWidget(self._field_group("Model", self.openrouter_model_input), 2)
        layout.addLayout(top_row)

        key_row = QHBoxLayout()
        key_row.setSpacing(12)
        key_row.addWidget(self._field_group("API key", self.openrouter_key_input), 2)
        key_options = QVBoxLayout()
        key_options.addWidget(self.ai_checkbox)
        key_options.addWidget(self.show_key_checkbox)
        key_row.addLayout(key_options, 1)
        layout.addLayout(key_row)
        layout.addWidget(self.ai_status_label)

        note = QLabel(
            "AI advice can prioritize cleanup and explain review items, but cleanup permissions stay deterministic."
        )
        note.setObjectName("InfoPill")
        note.setWordWrap(True)
        layout.addWidget(note)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        actions.addWidget(self.save_ai_button)
        actions.addWidget(self.test_ai_button)
        actions.addStretch()
        layout.addLayout(actions)
        return card

    def _build_exclusions_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)

        header = QWidget()
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)

        header_text = QWidget()
        header_text_layout = QVBoxLayout(header_text)
        header_text_layout.setContentsMargins(0, 0, 0, 0)
        header_text_layout.setSpacing(4)
        header_text_layout.addWidget(self._section_title("Excluded Folders"))
        header_text_layout.addWidget(
            self._section_description("Folders listed here are skipped during scans.")
        )

        header_layout.addWidget(header_text)
        header_layout.addStretch()
        header_layout.addWidget(self.add_exclusion_button)
        header_layout.addWidget(self.remove_exclusion_button)

        layout.addWidget(header)
        layout.addWidget(self.exclusions_list)
        return card

    def _build_data_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(self._section_title("Local Data"))
        layout.addWidget(
            self._section_description(
                "Scan summaries, cleanup reports, and rotating diagnostics stay on this device."
            )
        )
        layout.addStretch()

        first_row = QHBoxLayout()
        first_row.addWidget(self.clear_scans_button)
        first_row.addWidget(self.clear_reports_button)
        first_row.addStretch()
        layout.addLayout(first_row)

        second_row = QHBoxLayout()
        second_row.addWidget(self.clear_logs_button)
        second_row.addWidget(self.clear_history_button)
        second_row.addStretch()
        layout.addLayout(second_row)
        return card

    def _build_pro_card(self) -> Card:
        card = Card()
        layout = QVBoxLayout(card)
        layout.setContentsMargins(22, 20, 22, 20)
        layout.setSpacing(12)
        layout.addWidget(self._section_title("Planned Pro"))
        layout.addWidget(
            self._section_description(
                "Scheduled cleanup, advanced duplicate actions, and expanded AI tools are planned."
            )
        )
        plan = QLabel("Current plan: Free")
        plan.setObjectName("InfoPill")
        layout.addWidget(plan)
        layout.addStretch()

        row = QHBoxLayout()
        row.addWidget(self.upgrade_button)
        row.addStretch()
        layout.addLayout(row)
        return card

    def _section_title(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionTitle")
        return label

    def _section_description(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("SectionDescription")
        label.setWordWrap(True)
        return label

    def _field_label(self, text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("MutedText")
        return label

    def _field_group(self, label_text: str, field: QWidget) -> QWidget:
        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(self._field_label(label_text))
        layout.addWidget(field)
        return wrapper

    def on_theme_changed(self, theme: str) -> None:
        self.settings_service.set_theme(theme)
        app = QApplication.instance()
        if app is not None:
            apply_app_style(app, theme)

    def on_scan_mode_changed(self, mode: str) -> None:
        self.settings_service.set_scan_mode(mode)
        self.scan_mode_changed.emit(mode)

    def on_ai_provider_changed(self, provider: str) -> None:
        uses_openrouter = provider == "OpenRouter"
        self.openrouter_model_input.setEnabled(uses_openrouter)
        self.openrouter_key_input.setEnabled(uses_openrouter)
        self.show_key_checkbox.setEnabled(uses_openrouter)
        self.test_ai_button.setEnabled(uses_openrouter and self.ai_thread is None)
        self._update_ai_privacy_status()

    def on_ai_enabled_changed(self, enabled: bool) -> None:
        self.settings_service.set_ai_summary_enabled(enabled)
        self.ai_enabled_changed.emit(enabled)

    def on_privacy_mode_changed(self, enabled: bool) -> None:
        self.settings_service.set_privacy_mode(enabled)
        self._update_ai_privacy_status()

    def _update_ai_privacy_status(self) -> None:
        if self.ai_provider_combo.currentText() == "OpenRouter" and self.privacy_checkbox.isChecked():
            self.ai_status_label.setText(
                "Strict local mode is on. OpenRouter requests are blocked until it is turned off."
            )
        else:
            self.ai_status_label.setText("API keys are encrypted for this Windows account.")

    def refresh_exclusions(self) -> None:
        self.exclusions_list.clear()
        excluded = self.settings_service.get_excluded_folders()
        if not excluded:
            item = QListWidgetItem("No excluded folders added.")
            item.setData(Qt.ItemDataRole.UserRole, False)
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.exclusions_list.addItem(item)
            return

        for path in excluded:
            item = QListWidgetItem(str(path))
            item.setData(Qt.ItemDataRole.UserRole, True)
            self.exclusions_list.addItem(item)

    def add_exclusion(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Choose folder to exclude")
        if not folder:
            return
        path = Path(folder).resolve()
        if not path.exists() or not path.is_dir():
            QMessageBox.warning(self, "Invalid Folder", "Choose an existing folder to exclude.")
            return
        existing = {existing_path.resolve() for existing_path in self.settings_service.get_excluded_folders()}
        if path in existing:
            QMessageBox.information(self, "Already Excluded", "That folder is already excluded.")
            return
        self.settings_service.add_excluded_folder(path)
        self.refresh_exclusions()

    def remove_exclusion(self) -> None:
        item = self.exclusions_list.currentItem()
        if item is None or not item.data(Qt.ItemDataRole.UserRole):
            return
        self.settings_service.remove_excluded_folder(Path(item.text()))
        self.refresh_exclusions()

    def clear_scan_history(self) -> None:
        confirmed = QMessageBox.question(
            self,
            "Clear Scan History",
            "Clear saved scan sessions? Cleanup reports will be kept.",
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            self.settings_service.clear_scan_history()
            self.history_changed.emit()
            QMessageBox.information(self, "Scan History Cleared", "Saved scan sessions have been cleared.")

    def clear_cleanup_reports(self) -> None:
        confirmed = QMessageBox.question(
            self,
            "Clear Cleanup Reports",
            "Clear cleanup reports? Saved scan sessions will be kept.",
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            self.settings_service.clear_cleanup_reports()
            self.history_changed.emit()
            QMessageBox.information(self, "Cleanup Reports Cleared", "Cleanup reports have been cleared.")

    def clear_diagnostic_logs(self) -> None:
        confirmed = QMessageBox.question(
            self,
            "Clear Diagnostic Logs",
            "Clear rotating diagnostic logs stored on this device? Scan and cleanup history will be kept.",
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            try:
                self.settings_service.clear_diagnostic_logs()
            except OSError as exc:
                QMessageBox.warning(self, "Could Not Clear Logs", str(exc))
                return
            QMessageBox.information(self, "Diagnostic Logs Cleared", "Diagnostic logs have been cleared.")

    def clear_history(self) -> None:
        confirmed = QMessageBox.question(
            self,
            "Clear All Local History",
            "Clear all saved scan sessions and cleanup reports from SQLite?",
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            self.settings_service.clear_history()
            self.history_changed.emit()
            QMessageBox.information(self, "History Cleared", "Local history has been cleared.")

    def reset_settings(self) -> None:
        confirmed = QMessageBox.question(
            self,
            "Reset Settings",
            "Reset theme, scan mode, privacy, and AI preferences to defaults? Excluded folders are kept.",
        )
        if confirmed == QMessageBox.StandardButton.Yes:
            self.settings_service.reset_settings()
            self.theme_combo.setCurrentText(self.settings_service.get_theme())
            self.privacy_checkbox.setChecked(self.settings_service.privacy_mode_enabled())
            self.ai_checkbox.setChecked(self.settings_service.ai_summary_enabled())
            self.ai_provider_combo.setCurrentText(self.settings_service.get_ai_provider())
            self.openrouter_model_input.setText(self.settings_service.get_openrouter_model())
            self.openrouter_key_input.clear()
            self.scan_mode_combo.setCurrentText(self.settings_service.get_scan_mode())
            QMessageBox.information(self, "Settings Reset", "Settings have been reset to defaults.")

    def save_ai_settings(self) -> None:
        try:
            self._save_ai_settings_silently()
        except Exception as exc:
            QMessageBox.warning(self, "Could Not Save AI Settings", str(exc))
            return
        if self.ai_provider_combo.currentText() == "OpenRouter" and self.privacy_checkbox.isChecked():
            self._update_ai_privacy_status()
        else:
            self.ai_status_label.setText(
                "AI settings saved. The API key is encrypted with Windows DPAPI."
            )

    def _save_ai_settings_silently(self) -> None:
        if (
            self.ai_provider_combo.currentText() == "OpenRouter"
            and not self.openrouter_model_input.text().strip()
        ):
            raise ValueError("Enter an OpenRouter model name before saving.")
        self.settings_service.set_ai_provider(self.ai_provider_combo.currentText())
        self.settings_service.set_openrouter_model(self.openrouter_model_input.text())
        self.settings_service.set_openrouter_api_key(self.openrouter_key_input.text())
        self.settings_service.set_ai_summary_enabled(self.ai_checkbox.isChecked())

    def test_ai_settings(self) -> None:
        if self.ai_thread is not None:
            return
        try:
            self._save_ai_settings_silently()
        except Exception as exc:
            QMessageBox.warning(self, "Could Not Save AI Settings", str(exc))
            return
        self.test_ai_button.setEnabled(False)
        self.test_ai_button.setText("Testing...")
        self.ai_status_label.setText("Connecting to OpenRouter...")
        self.ai_thread = QThread()
        self.ai_worker = AiConnectionWorker(self.settings_service)
        self.ai_worker.moveToThread(self.ai_thread)
        self.ai_thread.started.connect(self.ai_worker.run)
        self.ai_worker.completed.connect(self.on_ai_test_completed)
        self.ai_worker.completed.connect(self.ai_thread.quit)
        self.ai_worker.failed.connect(self.on_ai_test_failed)
        self.ai_worker.failed.connect(self.ai_thread.quit)
        self.ai_thread.finished.connect(self.ai_worker.deleteLater)
        self.ai_thread.finished.connect(self.ai_thread.deleteLater)
        self.ai_thread.finished.connect(self._clear_ai_thread)
        self.ai_thread.start()

    def on_ai_test_completed(self, recommendation) -> None:
        self.ai_status_label.setText(recommendation.summary)

    def on_ai_test_failed(self, message: str) -> None:
        self.ai_status_label.setText(f"Connection test failed: {message}")

    def _clear_ai_thread(self) -> None:
        self.ai_thread = None
        self.ai_worker = None
        self.test_ai_button.setEnabled(True)
        self.test_ai_button.setText("Test OpenRouter")

    def show_pricing_dialog(self) -> None:
        PricingDialog(self.license_service, self).exec()

    def has_active_operation(self) -> bool:
        return self.ai_thread is not None

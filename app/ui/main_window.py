from __future__ import annotations

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QCloseEvent, QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.models import CleanupResult, ScanResult
from app.constants import APP_ICON_PATH, APP_NAME
from app.services.ai_advisor_service import AiAdvisorService
from app.services.cleanup_service import CleanupService
from app.services.license_service import MockLicenseService
from app.services.report_service import ReportService
from app.services.scan_service import ScanService
from app.services.settings_service import SettingsService
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.duplicates_page import DuplicatesPage
from app.ui.pages.large_files_page import LargeFilesPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.results_page import ResultsPage
from app.ui.pages.scan_page import ScanPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.icons import icon
from app.ui.onboarding_dialog import OnboardingDialog


class MainWindow(QMainWindow):
    def __init__(
        self,
        scan_service: ScanService,
        cleanup_service: CleanupService,
        report_service: ReportService,
        settings_service: SettingsService,
        ai_service: AiAdvisorService,
        license_service: MockLicenseService,
    ) -> None:
        super().__init__()
        self.settings_service = settings_service
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1120, 720)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.current_scan: ScanResult | None = None
        self._close_pending = False

        self.dashboard_page = DashboardPage(scan_service, report_service, ai_service)
        self.scan_page = ScanPage(scan_service, report_service, settings_service)
        self.results_page = ResultsPage(cleanup_service, ai_service)
        self.large_files_page = LargeFilesPage()
        self.duplicates_page = DuplicatesPage()
        self.reports_page = ReportsPage(report_service)
        self.settings_page = SettingsPage(settings_service, license_service)

        self.stack = QStackedWidget()
        self.stack.setObjectName("ContentStack")
        for page in [
            self.dashboard_page,
            self.scan_page,
            self.results_page,
            self.large_files_page,
            self.duplicates_page,
            self.reports_page,
            self.settings_page,
        ]:
            self.stack.addWidget(page)

        self.nav = QListWidget()
        self.nav.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.nav.setFixedHeight(410)
        self.nav.setIconSize(QSize(19, 19))
        nav_items = [
            ("Dashboard", "layout-dashboard"),
            ("Smart Scan", "scan-search"),
            ("Results", "list-checks"),
            ("Large Files", "files"),
            ("Duplicates", "copy"),
            ("Reports", "history"),
            ("Settings", "settings"),
        ]
        for label, icon_name in nav_items:
            item = QListWidgetItem(icon(icon_name, "#cbd5e1", 19), label)
            self.nav.addItem(item)
        self.nav.setCurrentRow(0)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)

        title = QLabel("DiskWise AI")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Local-first cleanup")
        subtitle.setObjectName("AppSubtitle")
        plan = QLabel(license_service.get_license_status().plan_name)
        plan.setObjectName("SidebarPlan")
        plan.setAlignment(Qt.AlignmentFlag.AlignCenter)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        sidebar.setFixedWidth(278)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(18, 22, 18, 22)
        sidebar_layout.setSpacing(8)
        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(4, 0, 0, 0)
        brand_layout.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(QIcon(str(APP_ICON_PATH)).pixmap(32, 32))
        brand_text = QWidget()
        brand_text_layout = QVBoxLayout(brand_text)
        brand_text_layout.setContentsMargins(0, 0, 0, 0)
        brand_text_layout.setSpacing(0)
        brand_text_layout.addWidget(title)
        brand_text_layout.addWidget(subtitle)
        brand_layout.addWidget(logo)
        brand_layout.addWidget(brand_text)
        brand_layout.addStretch()
        sidebar_layout.addWidget(brand)
        sidebar_layout.addSpacing(18)
        sidebar_layout.addWidget(self.nav)
        sidebar_layout.addStretch()
        sidebar_layout.addWidget(plan)

        root = QWidget()
        root.setObjectName("Root")
        root.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.stack)
        self.setCentralWidget(root)

        self.dashboard_page.start_scan_button.clicked.connect(lambda: self.nav.setCurrentRow(1))
        self.dashboard_page.start_scan_button.clicked.connect(self.scan_page.start_scan)
        self.dashboard_page.view_results_button.clicked.connect(lambda: self.nav.setCurrentRow(2))
        self.dashboard_page.clean_safe_button.clicked.connect(self.open_cleanup_preview)
        self.dashboard_page.view_latest_report_button.clicked.connect(lambda: self.nav.setCurrentRow(5))
        self.scan_page.scan_completed.connect(self.on_scan_completed)
        self.results_page.cleanup_completed.connect(self.on_cleanup_completed)
        self.settings_page.history_changed.connect(self.on_history_changed)
        self.settings_page.scan_mode_changed.connect(self.scan_page.mode_control.set_value)
        self.settings_page.scan_mode_changed.connect(self.scan_page.on_mode_changed)
        self.settings_page.scan_mode_changed.connect(self.dashboard_page.set_scan_mode)
        self.settings_page.ai_enabled_changed.connect(self.dashboard_page.set_ai_enabled)
        self.settings_page.ai_enabled_changed.connect(self.results_page.set_ai_enabled)
        self.settings_page.onboarding_requested.connect(lambda: self.show_onboarding(force=True))
        self.large_files_page.deep_scan_requested.connect(self.start_deep_scan)
        self.duplicates_page.deep_scan_requested.connect(self.start_deep_scan)
        self.dashboard_page.set_scan_mode(settings_service.get_scan_mode())
        self.dashboard_page.set_ai_enabled(settings_service.ai_summary_enabled())
        self.results_page.set_ai_enabled(settings_service.ai_summary_enabled())
        QTimer.singleShot(250, self.show_onboarding)

    def show_onboarding(self, force: bool = False) -> None:
        if not force and self.settings_service.onboarding_completed():
            return
        dialog = OnboardingDialog(self.settings_service, self)
        dialog.exec()
        mode = self.settings_service.get_scan_mode()
        self.scan_page.mode_control.set_value(mode)
        self.scan_page.on_mode_changed(mode)
        if dialog.start_scan_requested:
            self.nav.setCurrentRow(1)
            self.scan_page.start_scan()

    def start_deep_scan(self) -> None:
        self.nav.setCurrentRow(1)
        if self.scan_page.has_active_operation():
            return
        self.scan_page.mode_control.set_value("Deep")
        self.scan_page.on_mode_changed("Deep")
        self.dashboard_page.set_scan_mode("Deep")
        self.scan_page.start_scan()

    def open_cleanup_preview(self) -> None:
        self.nav.setCurrentRow(2)
        self.results_page.preview_cleanup()

    def _has_active_operations(self) -> bool:
        return any(
            (
                self.scan_page.has_active_operation(),
                self.results_page.has_active_operations(),
                self.dashboard_page.has_active_operation(),
                self.settings_page.has_active_operation(),
            )
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._has_active_operations():
            event.accept()
            return
        if self._close_pending:
            event.ignore()
            return

        answer = QMessageBox.question(
            self,
            "Operations Still Running",
            "DiskWise is still working. Cancel file operations and close after background work finishes?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            event.ignore()
            return

        self._close_pending = True
        self.scan_page.cancel_active_operation()
        self.results_page.cancel_active_operations()
        event.ignore()
        QTimer.singleShot(250, self._finish_close_when_idle)

    def _finish_close_when_idle(self) -> None:
        if self._has_active_operations():
            QTimer.singleShot(250, self._finish_close_when_idle)
            return
        self.close()

    def on_scan_completed(self, result: ScanResult) -> None:
        self.current_scan = result
        self.dashboard_page.set_scan_result(result)
        self.results_page.set_scan_result(result)
        self.large_files_page.set_scan_result(result)
        self.duplicates_page.set_scan_result(result)
        self.reports_page.refresh()
        self.dashboard_page.load_persisted_summary()
        if not result.canceled:
            self.nav.setCurrentRow(2)

    def on_history_changed(self) -> None:
        self.reports_page.refresh()
        self.dashboard_page.load_persisted_summary()

    def on_cleanup_completed(self, _result: CleanupResult) -> None:
        self.current_scan = self.results_page.current_scan
        self.reports_page.refresh()
        self.dashboard_page.refresh_disk_usage()
        self.dashboard_page.load_persisted_summary()
        if self.current_scan is not None:
            self.dashboard_page.set_scan_result(self.current_scan)

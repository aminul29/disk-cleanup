from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from app.models import ScanResult
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
        self.setWindowTitle(APP_NAME)
        if APP_ICON_PATH.exists():
            self.setWindowIcon(QIcon(str(APP_ICON_PATH)))
        self.current_scan: ScanResult | None = None

        self.dashboard_page = DashboardPage(scan_service, report_service, ai_service)
        self.scan_page = ScanPage(scan_service, report_service)
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
        nav_items = [
            "Dashboard",
            "Smart Scan",
            "Results",
            "Large Files",
            "Duplicates",
            "Reports",
            "Settings",
        ]
        for item in nav_items:
            self.nav.addItem(QListWidgetItem(item))
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
        sidebar_layout.addWidget(title)
        sidebar_layout.addWidget(subtitle)
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
        self.dashboard_page.clean_safe_button.clicked.connect(lambda: self.nav.setCurrentRow(2))
        self.dashboard_page.view_latest_report_button.clicked.connect(lambda: self.nav.setCurrentRow(5))
        self.scan_page.scan_completed.connect(self.on_scan_completed)
        self.settings_page.history_changed.connect(self.on_history_changed)

    def on_scan_completed(self, result: ScanResult) -> None:
        self.current_scan = result
        self.dashboard_page.set_scan_result(result)
        self.results_page.set_scan_result(result)
        self.large_files_page.set_scan_result(result)
        self.duplicates_page.set_scan_result(result)
        self.reports_page.refresh()
        self.dashboard_page.load_persisted_summary()
        self.nav.setCurrentRow(2)

    def on_history_changed(self) -> None:
        self.reports_page.refresh()
        self.dashboard_page.load_persisted_summary()

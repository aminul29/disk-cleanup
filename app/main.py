from __future__ import annotations

import sys
import logging

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication
from PySide6.QtWidgets import QMessageBox

from app.constants import (
    APP_AUTHOR,
    APP_ICON_PATH,
    APP_ID,
    APP_NAME,
    APP_VERSION,
    DATABASE_PATH,
)
from app.database.local_database import LocalDatabase
from app.runtime import SingleInstanceGuard, configure_logging
from app.services.ai_advisor_service import AiAdvisorService
from app.services.cleanup_service import CleanupService
from app.services.license_service import MockLicenseService
from app.services.report_service import ReportService
from app.services.scan_service import ScanService
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow
from app.ui.styles import apply_app_style


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName(APP_AUTHOR)
    if APP_ICON_PATH.exists():
        app.setWindowIcon(QIcon(str(APP_ICON_PATH)))

    configure_logging()
    logger = logging.getLogger(__name__)
    logger.info("Starting %s %s", APP_NAME, APP_VERSION)

    instance_guard = SingleInstanceGuard(APP_ID)
    if instance_guard.is_another_instance_running():
        QMessageBox.information(
            None,
            APP_NAME,
            "DiskWise AI is already running.",
        )
        return 0

    try:
        DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

        database = LocalDatabase(DATABASE_PATH)
        database.initialize()

        settings_service = SettingsService(database)
        scan_service = ScanService(settings_service)
        report_service = ReportService(database)
        cleanup_service = CleanupService(report_service)
        ai_service = AiAdvisorService(settings_service)
        license_service = MockLicenseService()

        apply_app_style(app, settings_service.get_theme())
        app.styleHints().colorSchemeChanged.connect(
            lambda _scheme: apply_app_style(app, settings_service.get_theme())
            if settings_service.get_theme() == "System"
            else None
        )

        window = MainWindow(
            scan_service=scan_service,
            cleanup_service=cleanup_service,
            report_service=report_service,
            settings_service=settings_service,
            ai_service=ai_service,
            license_service=license_service,
        )
        window.resize(1280, 820)
        window.show()
    except Exception as exc:  # pragma: no cover - startup safety net
        logger.exception("Startup failed")
        QMessageBox.critical(
            None,
            APP_NAME,
            "DiskWise AI could not start.\n\n"
            f"{exc}\n\n"
            "A diagnostic log was written to the local app data log folder.",
        )
        return 1

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

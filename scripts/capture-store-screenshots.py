from __future__ import annotations

# ruff: noqa: E402

import argparse
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_SCALE_FACTOR", "1")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from app.database.local_database import LocalDatabase
from app.models import (
    AiRecommendation,
    CleanupCategory,
    CleanupItem,
    CleanupResult,
    DuplicateGroup,
    RiskLevel,
    ScanMode,
    ScanResult,
)
from app.services.ai_advisor_service import AiAdvisorService
from app.services.cleanup_service import CleanupService
from app.services.license_service import MockLicenseService
from app.services.report_service import ReportService
from app.services.scan_service import ScanService
from app.services.settings_service import SettingsService
from app.ui.main_window import MainWindow
from app.ui.styles import apply_app_style

MIB = 1024 * 1024
GIB = 1024 * MIB
DEMO_ROOT = Path(r"C:\Users\Demo")
DEMO_TIME = datetime(2026, 7, 15, 2, 32, 0)


def demo_item(
    item_id: str,
    relative_path: str,
    size_bytes: int,
    category: str,
    risk: RiskLevel,
    reason: str,
    modified: datetime,
) -> CleanupItem:
    path = DEMO_ROOT / relative_path
    return CleanupItem(
        id=item_id,
        file_name=path.name,
        file_path=str(path),
        extension=path.suffix,
        size_bytes=size_bytes,
        last_modified_at=modified,
        category=category,
        risk_level=risk,
        reason=reason,
        can_delete=risk == RiskLevel.SAFE,
        is_selected=risk == RiskLevel.SAFE,
    )


def demo_category(
    category_id: str,
    name: str,
    description: str,
    risk: RiskLevel,
    items: list[CleanupItem],
) -> CleanupCategory:
    return CleanupCategory(
        id=category_id,
        name=name,
        description=description,
        risk_level=risk,
        total_bytes=sum(item.size_bytes for item in items),
        file_count=len(items),
        items=items,
        is_selected_by_default=risk == RiskLevel.SAFE,
    )


def build_demo_scan() -> ScanResult:
    safe_items = {
        "user_temp": [
            demo_item(
                "temp-1",
                r"AppData\Local\Temp\render-cache.tmp",
                126 * MIB,
                "user_temp",
                RiskLevel.SAFE,
                "Temporary file in a user-level temp folder.",
                datetime(2026, 7, 13, 9, 18),
            ),
            demo_item(
                "temp-2",
                r"AppData\Local\Temp\update-stage.tmp",
                82 * MIB,
                "user_temp",
                RiskLevel.SAFE,
                "Temporary file in a user-level temp folder.",
                datetime(2026, 7, 12, 16, 4),
            ),
        ],
        "browser_cache": [
            demo_item(
                "browser-1",
                r"AppData\Local\Browser\Default\Cache\data_01.cache",
                214 * MIB,
                "browser_cache",
                RiskLevel.SAFE,
                "Browser cache file stored under the user profile.",
                datetime(2026, 7, 15, 1, 44),
            ),
            demo_item(
                "browser-2",
                r"AppData\Local\Browser\Profile 1\Code Cache\code_02.cache",
                158 * MIB,
                "browser_cache",
                RiskLevel.SAFE,
                "Browser cache file stored under the user profile.",
                datetime(2026, 7, 14, 22, 8),
            ),
            demo_item(
                "browser-3",
                r"AppData\Local\Browser\Default\GPUCache\gpu_03.cache",
                94 * MIB,
                "browser_cache",
                RiskLevel.SAFE,
                "Browser cache file stored under the user profile.",
                datetime(2026, 7, 14, 20, 31),
            ),
        ],
        "thumbnail_cache": [
            demo_item(
                "thumb-1",
                r"AppData\Local\Microsoft\Windows\Explorer\thumbcache_256.db",
                36 * MIB,
                "thumbnail_cache",
                RiskLevel.SAFE,
                "Windows thumbnail cache for this user account.",
                datetime(2026, 7, 14, 18, 55),
            )
        ],
        "app_cache": [
            demo_item(
                "app-1",
                r"AppData\Local\CrashDumps\media-app.dmp",
                68 * MIB,
                "app_cache",
                RiskLevel.SAFE,
                "Crash dump in a user-level cache folder.",
                datetime(2026, 7, 10, 11, 9),
            ),
            demo_item(
                "app-2",
                r"AppData\Local\Microsoft\Windows\INetCache\session.log",
                24 * MIB,
                "app_cache",
                RiskLevel.SAFE,
                "Log file in a known user-level cache folder.",
                datetime(2026, 7, 11, 8, 20),
            ),
        ],
    }

    old_downloads = [
        demo_item(
            "download-1",
            r"Downloads\video-editor-setup.exe",
            940 * MIB,
            "old_downloads",
            RiskLevel.REVIEW,
            "Old installer in Downloads. Confirm it is no longer needed.",
            datetime(2025, 11, 8, 12, 14),
        ),
        demo_item(
            "download-2",
            r"Downloads\project-archive.7z",
            1800 * MIB,
            "old_downloads",
            RiskLevel.REVIEW,
            "Large archive in Downloads. Review its contents first.",
            datetime(2025, 8, 17, 17, 42),
        ),
        demo_item(
            "download-3",
            r"Downloads\windows-lab.iso",
            5100 * MIB,
            "old_downloads",
            RiskLevel.REVIEW,
            "Disk image in Downloads. Keep it if it is still used.",
            datetime(2025, 4, 22, 10, 6),
        ),
    ]
    large_files = [
        *old_downloads,
        demo_item(
            "large-1",
            r"Videos\conference-recording.mp4",
            3200 * MIB,
            "large_files",
            RiskLevel.REVIEW,
            "Large personal video. Review before deleting.",
            datetime(2025, 2, 3, 19, 22),
        ),
        demo_item(
            "large-2",
            r"Documents\Design\prototype-export.zip",
            1450 * MIB,
            "large_files",
            RiskLevel.REVIEW,
            "Large archive in a protected personal folder.",
            datetime(2024, 12, 11, 9, 35),
        ),
    ]
    large_category_items = large_files[len(old_downloads) :]

    duplicate_a = [
        demo_item(
            "dup-a-1",
            r"Downloads\reference-library.zip",
            512 * MIB,
            "duplicates",
            RiskLevel.REVIEW,
            "Duplicate candidate. Review every copy.",
            datetime(2025, 9, 6, 10, 0),
        ),
        demo_item(
            "dup-a-2",
            r"Downloads\Archive\reference-library.zip",
            512 * MIB,
            "duplicates",
            RiskLevel.REVIEW,
            "Duplicate candidate. Review every copy.",
            datetime(2025, 9, 8, 15, 30),
        ),
    ]
    duplicate_b = [
        demo_item(
            "dup-b-1",
            r"Downloads\camera-export.mov",
            286 * MIB,
            "duplicates",
            RiskLevel.REVIEW,
            "Duplicate candidate. Review every copy.",
            datetime(2025, 6, 2, 12, 40),
        ),
        demo_item(
            "dup-b-2",
            r"Downloads\Shared\camera-export.mov",
            286 * MIB,
            "duplicates",
            RiskLevel.REVIEW,
            "Duplicate candidate. Review every copy.",
            datetime(2025, 6, 3, 8, 15),
        ),
        demo_item(
            "dup-b-3",
            r"Downloads\Backup\camera-export.mov",
            286 * MIB,
            "duplicates",
            RiskLevel.REVIEW,
            "Duplicate candidate. Review every copy.",
            datetime(2025, 6, 3, 8, 18),
        ),
    ]

    categories = [
        demo_category(
            "user_temp",
            "User Temporary Files",
            "Temporary files from user-level temp folders.",
            RiskLevel.SAFE,
            safe_items["user_temp"],
        ),
        demo_category(
            "browser_cache",
            "Browser Cache",
            "Cache files from accessible browser profiles.",
            RiskLevel.SAFE,
            safe_items["browser_cache"],
        ),
        demo_category(
            "thumbnail_cache",
            "Thumbnail Cache",
            "Windows thumbnail cache files for this user.",
            RiskLevel.SAFE,
            safe_items["thumbnail_cache"],
        ),
        demo_category(
            "app_cache",
            "User App Cache",
            "Crash dumps and logs in known user-level cache folders.",
            RiskLevel.SAFE,
            safe_items["app_cache"],
        ),
        demo_category(
            "old_downloads",
            "Old Downloads",
            "Downloads that require a manual decision.",
            RiskLevel.REVIEW,
            old_downloads,
        ),
        demo_category(
            "large_files",
            "Large Files",
            "Large personal files that are never cleaned automatically.",
            RiskLevel.REVIEW,
            large_category_items,
        ),
        demo_category(
            "protected_personal_folders",
            "Protected Personal Folders",
            "Documents, Desktop, Pictures, Videos, and Music remain protected.",
            RiskLevel.PROTECTED,
            [],
        ),
    ]
    duplicates = [
        DuplicateGroup(
            id="demo-duplicate-1",
            file_size_bytes=512 * MIB,
            hash="demo-hash-reference-library",
            files=duplicate_a,
            suggested_keep_file_path=duplicate_a[0].file_path,
            potential_savings_bytes=512 * MIB,
        ),
        DuplicateGroup(
            id="demo-duplicate-2",
            file_size_bytes=286 * MIB,
            hash="demo-hash-camera-export",
            files=duplicate_b,
            suggested_keep_file_path=duplicate_b[0].file_path,
            potential_savings_bytes=572 * MIB,
        ),
    ]

    return ScanResult(
        scan_id="store-demo-scan",
        started_at=datetime(2026, 7, 15, 2, 31, 6),
        completed_at=DEMO_TIME,
        duration_seconds=54.2,
        total_files_scanned=sum(category.file_count for category in categories),
        total_bytes_scanned=sum(category.total_bytes for category in categories),
        safe_bytes=sum(
            category.total_bytes
            for category in categories
            if category.risk_level == RiskLevel.SAFE
        ),
        review_bytes=sum(
            category.total_bytes
            for category in categories
            if category.risk_level == RiskLevel.REVIEW
        ),
        protected_bytes=0,
        mode=ScanMode.DEEP,
        categories=categories,
        large_files=large_files,
        duplicate_groups=duplicates,
        errors=[],
    )


def seed_demo_history(report_service: ReportService, scan: ScanResult) -> None:
    report_service.save_scan(scan)
    report_service.create_cleanup_report(
        CleanupResult(
            scan_id="store-demo-previous-scan",
            started_at=datetime(2026, 7, 14, 10, 18, 0),
            completed_at=datetime(2026, 7, 14, 10, 20, 12),
            files_deleted=1421,
            files_skipped=3,
            bytes_recovered=482 * MIB,
            categories_cleaned=["browser_cache", "user_temp"],
            errors=["3 files were locked and skipped safely."],
            duration_seconds=132.0,
            free_space_before_bytes=187 * GIB,
            free_space_after_bytes=187 * GIB,
        )
    )


def capture_page(
    app: QApplication,
    window: MainWindow,
    nav_index: int,
    destination: Path,
) -> None:
    window.nav.setCurrentRow(nav_index)
    window.raise_()
    window.activateWindow()
    window.repaint()
    app.processEvents()
    QTest.qWait(300)
    pixmap = window.grab()
    for _attempt in range(6):
        if screenshot_has_branding(pixmap):
            break
        window.repaint()
        app.processEvents()
        QTest.qWait(120)
        pixmap = window.grab()
    else:
        raise RuntimeError(f"Screenshot did not render completely: {destination.name}")
    if pixmap.width() < 1366 or pixmap.height() < 768:
        raise RuntimeError(
            f"Screenshot is too small for Store use: {pixmap.width()}x{pixmap.height()}"
        )
    if not pixmap.save(str(destination), "PNG"):
        raise RuntimeError(f"Could not save screenshot: {destination}")


def screenshot_has_branding(pixmap) -> bool:
    image = pixmap.toImage()
    ratio = max(pixmap.devicePixelRatio(), 1.0)
    left = round(24 * ratio)
    right = min(round(260 * ratio), image.width())
    top = round(26 * ratio)
    bottom = min(round(105 * ratio), image.height())
    bright_pixels = 0
    for y in range(top, bottom, 3):
        for x in range(left, right, 3):
            color = image.pixelColor(x, y)
            if max(color.red(), color.green(), color.blue()) >= 150:
                bright_pixels += 1
    return bright_pixels >= 80


def capture_store_screenshots(output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    app = QApplication.instance() or QApplication([])
    app.setApplicationName("DiskWise AI Store Media")

    with tempfile.TemporaryDirectory(prefix="diskwise-store-media-") as temp_dir:
        database = LocalDatabase(Path(temp_dir) / "store-media.db")
        database.initialize()
        settings = SettingsService(database)
        settings.set_theme("Dark")
        settings.set_scan_mode("Deep")
        settings.set_ai_provider("Mock")
        settings.set_ai_summary_enabled(True)
        settings.set_onboarding_completed(True)

        report_service = ReportService(database)
        scan = build_demo_scan()
        seed_demo_history(report_service, scan)
        scan_service = ScanService(settings)
        ai_service = AiAdvisorService(settings)
        window = MainWindow(
            scan_service=scan_service,
            cleanup_service=CleanupService(report_service),
            report_service=report_service,
            settings_service=settings,
            ai_service=ai_service,
            license_service=MockLicenseService(),
        )
        apply_app_style(app, "Dark")
        window.resize(1440, 810)
        window.show()
        app.processEvents()
        QTest.qWait(320)

        window.current_scan = scan
        window.dashboard_page.set_scan_result(scan)
        window.dashboard_page.storage_card.set_values(
            "187.6 GB",
            r"C:\ free of 476.8 GB (61% used)",
        )
        window.results_page.set_scan_result(scan)
        window.large_files_page.set_scan_result(scan)
        window.duplicates_page.set_scan_result(scan)
        window.reports_page.refresh()
        window.dashboard_page.set_scan_mode("Deep")

        captured: list[Path] = []
        for nav_index, file_name in [
            (0, "01-dashboard.png"),
            (2, "02-results.png"),
        ]:
            destination = output_dir / file_name
            capture_page(app, window, nav_index, destination)
            captured.append(destination)

        window.results_page.on_ai_completed(
            AiRecommendation(
                summary=(
                    "Safe cache cleanup is ready. Old installers and duplicate candidates "
                    "should be reviewed separately."
                ),
                safe_cleanup_plan=[
                    "Preview the selected cache and temporary files.",
                    "Move only the selected Safe items to the Recycle Bin.",
                ],
                review_priorities=[
                    "Review the old disk image in Downloads.",
                    "Compare both duplicate groups before removing any copy.",
                ],
                warnings=["Review items remain excluded from DiskWise cleanup."],
                confidence="High",
            )
        )
        ai_destination = output_dir / "03-ai-advice.png"
        capture_page(app, window, 2, ai_destination)
        captured.append(ai_destination)

        for nav_index, file_name in [
            (3, "04-large-files.png"),
            (4, "05-duplicates.png"),
            (5, "06-reports.png"),
        ]:
            destination = output_dir / file_name
            capture_page(app, window, nav_index, destination)
            captured.append(destination)

        window.close()
        app.processEvents()
        return captured


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture privacy-safe Microsoft Store screenshots from the real DiskWise UI."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "packaging" / "store" / "screenshots",
        help="Directory where PNG screenshots are written.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    paths = capture_store_screenshots(args.output.resolve())
    for screenshot in paths:
        print(screenshot)

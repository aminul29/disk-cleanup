from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from app.database.local_database import LocalDatabase
from app.models import RiskLevel
from app.services.scan_service import ScanService
from app.services.settings_service import SettingsService


def make_scan_service(tmp_path: Path) -> ScanService:
    database = LocalDatabase(tmp_path / "settings.db")
    database.initialize()
    return ScanService(SettingsService(database))


def test_old_downloads_are_review_only(monkeypatch, tmp_path: Path) -> None:
    downloads = tmp_path / "Downloads"
    downloads.mkdir()
    installer = downloads / "setup.exe"
    installer.write_bytes(b"x" * 1024)
    old_time = (datetime.now() - timedelta(days=120)).timestamp()
    os.utime(installer, (old_time, old_time))

    monkeypatch.setattr("app.services.scan_service.downloads_path", lambda: downloads)

    service = make_scan_service(tmp_path)
    items = service._scan_old_downloads([], None, None, [])

    assert len(items) == 1
    assert items[0].risk_level == RiskLevel.REVIEW
    assert items[0].can_delete is False
    assert items[0].is_selected is False


def test_safe_category_defaults_to_selected(tmp_path: Path) -> None:
    service = make_scan_service(tmp_path)
    file_path = tmp_path / "cache.tmp"
    file_path.write_text("cache")
    item = service._create_item(
        file_path,
        "user_temp",
        RiskLevel.SAFE,
        "temporary file",
        True,
    )

    assert item is not None
    category = service._build_category(
        "user_temp",
        "User Temp",
        "Temporary files.",
        RiskLevel.SAFE,
        [item],
        True,
    )

    assert category.file_count == 1
    assert category.total_bytes == file_path.stat().st_size
    assert category.risk_level == RiskLevel.SAFE
    assert category.is_selected_by_default is True

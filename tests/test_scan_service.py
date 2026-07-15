from __future__ import annotations

import os
from datetime import datetime, timedelta
from pathlib import Path

from app.database.local_database import LocalDatabase
from app.models import RiskLevel, ScanMode
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


def test_quick_scan_skips_deep_analysis(monkeypatch, tmp_path: Path) -> None:
    service = make_scan_service(tmp_path)
    monkeypatch.setattr("app.services.scan_service.temp_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.browser_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.thumbnail_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.app_cache_locations", lambda: [])

    def unexpected_call(**kwargs):
        raise AssertionError("Quick scan invoked a Deep-only scanner")

    monkeypatch.setattr(service, "_scan_old_downloads", unexpected_call)
    monkeypatch.setattr(service, "_scan_large_files", unexpected_call)
    monkeypatch.setattr(service, "_scan_duplicate_candidates", unexpected_call)

    result = service.scan(ScanMode.QUICK)

    assert result.mode == ScanMode.QUICK
    assert result.large_files == []
    assert result.duplicate_groups == []
    assert all(category.risk_level != RiskLevel.REVIEW for category in result.categories)


def test_deep_scan_runs_review_analysis(monkeypatch, tmp_path: Path) -> None:
    service = make_scan_service(tmp_path)
    monkeypatch.setattr("app.services.scan_service.temp_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.browser_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.thumbnail_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.app_cache_locations", lambda: [])
    called: list[str] = []
    monkeypatch.setattr(
        service,
        "_scan_old_downloads",
        lambda **kwargs: called.append("downloads") or [],
    )
    monkeypatch.setattr(
        service,
        "_scan_large_files",
        lambda **kwargs: called.append("large") or [],
    )
    monkeypatch.setattr(
        service,
        "_scan_duplicate_candidates",
        lambda **kwargs: called.append("duplicates") or [],
    )

    result = service.scan(ScanMode.DEEP)

    assert called == ["downloads", "large", "duplicates"]
    assert result.mode == ScanMode.DEEP
    assert {category.id for category in result.categories} >= {"old_downloads", "large_files"}


def test_deep_scan_does_not_double_count_large_downloads(monkeypatch, tmp_path: Path) -> None:
    service = make_scan_service(tmp_path)
    monkeypatch.setattr("app.services.scan_service.temp_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.browser_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.thumbnail_cache_locations", lambda: [])
    monkeypatch.setattr("app.services.scan_service.app_cache_locations", lambda: [])
    download = tmp_path / "Downloads" / "large.zip"
    download.parent.mkdir()
    download.write_bytes(b"large download")
    old_download = service._create_item(
        download, "old_downloads", RiskLevel.REVIEW, "Old download", False
    )
    large_file = service._create_item(
        download, "large_files", RiskLevel.REVIEW, "Large file", False
    )
    assert old_download is not None and large_file is not None
    monkeypatch.setattr(service, "_scan_old_downloads", lambda **kwargs: [old_download])
    monkeypatch.setattr(service, "_scan_large_files", lambda **kwargs: [large_file])
    monkeypatch.setattr(service, "_scan_duplicate_candidates", lambda **kwargs: [])

    result = service.scan(ScanMode.DEEP)
    categories = {category.id: category for category in result.categories}

    assert result.review_bytes == download.stat().st_size
    assert categories["old_downloads"].file_count == 1
    assert categories["large_files"].file_count == 0
    assert result.large_files == [large_file]


def test_safe_scan_deduplicates_nested_roots(tmp_path: Path) -> None:
    service = make_scan_service(tmp_path)
    root = tmp_path / "cache"
    nested = root / "Cache_Data"
    nested.mkdir(parents=True)
    (nested / "entry.cache").write_text("cache")

    items = service._scan_safe_locations(
        category="browser_cache",
        locations=[root, nested],
        reason="Browser cache",
        excluded=[],
        progress_name="Browser cache",
        progress_callback=None,
        cancel_event=None,
        errors=[],
        progress=45,
    )

    assert len(items) == 1
    assert service._minimal_roots([root, nested]) == [root]


def test_excluding_child_folder_does_not_skip_parent(tmp_path: Path) -> None:
    service = make_scan_service(tmp_path)
    root = tmp_path / "Documents"
    excluded = root / "excluded"
    included = root / "included"
    excluded.mkdir(parents=True)
    included.mkdir()
    (excluded / "skip.txt").write_text("skip")
    keep = included / "keep.txt"
    keep.write_text("keep")

    files = list(service._walk_files(root, [excluded], None, []))

    assert files == [keep]

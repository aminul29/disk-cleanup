from __future__ import annotations

from pathlib import Path

from app.utils import paths


def test_browser_cache_locations_include_multiple_chromium_profiles(
    monkeypatch,
    tmp_path: Path,
) -> None:
    local = tmp_path / "Local"
    roaming = tmp_path / "Roaming"
    expected = [
        local / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
        local / "Google" / "Chrome" / "User Data" / "Profile 2" / "Code Cache",
        local / "Microsoft" / "Edge" / "User Data" / "Profile 1" / "GPUCache",
    ]
    for location in expected:
        location.mkdir(parents=True)
    monkeypatch.setattr(paths, "local_app_data", lambda: local)
    monkeypatch.setattr(paths, "roaming_app_data", lambda: roaming)

    discovered = paths.browser_cache_locations()

    assert set(expected) <= set(discovered)

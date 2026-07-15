from __future__ import annotations

import os
import tempfile
from pathlib import Path


def user_profile() -> Path:
    return Path.home()


def local_app_data() -> Path:
    return Path(os.environ.get("LOCALAPPDATA", user_profile() / "AppData" / "Local"))


def roaming_app_data() -> Path:
    return Path(os.environ.get("APPDATA", user_profile() / "AppData" / "Roaming"))


def temp_locations() -> list[Path]:
    locations = [Path(tempfile.gettempdir()), local_app_data() / "Temp"]
    return unique_existing_paths(locations)


def browser_cache_locations() -> list[Path]:
    local = local_app_data()
    roaming = roaming_app_data()
    locations: list[Path] = []

    chromium_roots = [
        local / "Google" / "Chrome" / "User Data",
        local / "Microsoft" / "Edge" / "User Data",
        local / "BraveSoftware" / "Brave-Browser" / "User Data",
        local / "Vivaldi" / "User Data",
    ]
    for profile_root in chromium_roots:
        for profile in _browser_profile_directories(profile_root):
            locations.extend(
                [
                    profile / "Cache",
                    profile / "Code Cache",
                    profile / "GPUCache",
                    profile / "Service Worker" / "CacheStorage",
                ]
            )

    locations.extend(
        [
            local / "Opera Software" / "Opera Stable" / "Cache",
            roaming / "Opera Software" / "Opera Stable" / "Cache",
        ]
    )

    for profile_root in [
        local / "Mozilla" / "Firefox" / "Profiles",
        roaming / "Mozilla" / "Firefox" / "Profiles",
    ]:
        if not profile_root.exists():
            continue
        try:
            profiles = list(profile_root.iterdir())
        except OSError:
            continue
        for profile in profiles:
            try:
                is_profile_dir = profile.is_dir()
            except OSError:
                continue
            if is_profile_dir:
                locations.extend(
                    [
                        profile / "cache2",
                        profile / "cache2" / "entries",
                        profile / "startupCache",
                    ]
                )
    return unique_existing_paths(locations)


def _browser_profile_directories(profile_root: Path) -> list[Path]:
    if not profile_root.exists():
        return []
    try:
        candidates = list(profile_root.iterdir())
    except OSError:
        return []

    profile_names = {"Default", "Guest Profile", "System Profile"}
    profiles: list[Path] = []
    for candidate in candidates:
        if candidate.name not in profile_names and not candidate.name.startswith("Profile "):
            continue
        try:
            if candidate.is_dir():
                profiles.append(candidate)
        except OSError:
            continue
    return profiles


def thumbnail_cache_locations() -> list[Path]:
    locations = [
        local_app_data() / "Microsoft" / "Windows" / "Explorer",
    ]
    return unique_existing_paths(locations)


def app_cache_locations() -> list[Path]:
    local = local_app_data()
    locations = [
        local / "CrashDumps",
        local / "Microsoft" / "Windows" / "INetCache",
    ]
    return unique_existing_paths(locations)


def downloads_path() -> Path:
    return user_profile() / "Downloads"


def personal_scan_locations() -> list[Path]:
    home = user_profile()
    locations = [
        home / "Downloads",
        home / "Desktop",
        home / "Documents",
        home / "Videos",
        home / "Pictures",
        home / "Music",
    ]
    return unique_existing_paths(locations)


def unique_existing_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            resolved = str(path.resolve()).lower()
        except OSError:
            resolved = str(path).lower()
        if resolved not in seen and path.exists():
            seen.add(resolved)
            result.append(path)
    return result


def is_under(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except (OSError, ValueError):
        return False

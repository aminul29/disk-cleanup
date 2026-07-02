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
    locations: list[Path] = [
        local / "Google" / "Chrome" / "User Data" / "Default" / "Cache",
        local / "Google" / "Chrome" / "User Data" / "Default" / "Cache" / "Cache_Data",
        local / "Google" / "Chrome" / "User Data" / "Default" / "Code Cache",
        local / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache",
        local / "Microsoft" / "Edge" / "User Data" / "Default" / "Cache" / "Cache_Data",
        local / "Microsoft" / "Edge" / "User Data" / "Default" / "Code Cache",
        local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Cache",
        local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Code Cache",
        local / "Opera Software" / "Opera Stable" / "Cache",
    ]

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

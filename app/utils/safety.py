from __future__ import annotations

from pathlib import Path

from app.utils.paths import (
    app_cache_locations,
    browser_cache_locations,
    is_under,
    temp_locations,
    thumbnail_cache_locations,
    user_profile,
)


PROTECTED_FOLDER_NAMES = {
    ".git",
    ".svn",
    ".hg",
    "1password",
    "bitwarden",
    "keepass",
    "keepassxc",
    "passwords",
    "accounting",
    "bookkeeping",
    "finance",
    "financial",
    "quickbooks",
    "quicken",
    "taxes",
    "source",
    "src",
    "repos",
    "repositories",
    "node_modules",
    ".venv",
    "venv",
}

PROTECTED_FILE_EXTENSIONS = {
    ".1pif",
    ".1pux",
    ".enpassbackup",
    ".iif",
    ".kdb",
    ".kdbx",
    ".key",
    ".ofx",
    ".p12",
    ".pem",
    ".pfx",
    ".psafe3",
    ".qbb",
    ".qbm",
    ".qbo",
    ".qbw",
    ".qfx",
}


def default_protected_roots() -> list[Path]:
    home = user_profile()
    roots = [
        Path("C:/Windows"),
        Path("C:/Windows/System32"),
        Path("C:/Program Files"),
        Path("C:/Program Files (x86)"),
        Path("C:/Program Files/WindowsApps"),
        home / "Desktop",
        home / "Documents",
        home / "Pictures",
        home / "Videos",
        home / "Music",
    ]
    return [root for root in roots if root.exists()]


def default_safe_cleanup_roots() -> list[Path]:
    return [
        *temp_locations(),
        *browser_cache_locations(),
        *thumbnail_cache_locations(),
        *app_cache_locations(),
    ]


def is_protected_path(path: Path, protected_roots: list[Path] | None = None) -> bool:
    roots = protected_roots if protected_roots is not None else default_protected_roots()
    if any(is_under(path, root) for root in roots):
        return True

    path_parts = {part.lower() for part in path.parts}
    if any(folder_name in path_parts for folder_name in PROTECTED_FOLDER_NAMES):
        return True

    suffix = path.suffix.lower()
    is_tax_file = suffix == ".tax" or (
        suffix.startswith(".tax") and suffix.removeprefix(".tax").isdigit()
    )
    return suffix in PROTECTED_FILE_EXTENSIONS or is_tax_file


def is_safe_cleanup_path(
    path: Path,
    safe_roots: list[Path] | None = None,
    protected_roots: list[Path] | None = None,
) -> bool:
    if is_protected_path(path, protected_roots):
        return False
    roots = safe_roots if safe_roots is not None else default_safe_cleanup_roots()
    return any(is_under(path, root) for root in roots)

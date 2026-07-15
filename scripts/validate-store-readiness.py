from __future__ import annotations

import argparse
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "packaging" / "msix" / "AppxManifest.template.xml"
ASSETS_DIR = ROOT / "packaging" / "msix" / "Assets"
SCREENSHOTS_DIR = ROOT / "packaging" / "store" / "screenshots"
LISTING_PATH = ROOT / "app" / "docs" / "store-listing.md"
PRIVACY_PATH = ROOT / "app" / "docs" / "privacy-policy.md"
CERTIFICATION_NOTES_PATH = ROOT / "app" / "docs" / "store-certification-notes.md"
DIST_DIR = ROOT / "dist" / "DiskWiseAI"

FOUNDATION_NS = "http://schemas.microsoft.com/appx/manifest/foundation/windows10"
UAP_NS = "http://schemas.microsoft.com/appx/manifest/uap/windows10"
RESCAP_NS = "http://schemas.microsoft.com/appx/manifest/foundation/windows10/restrictedcapabilities"

EXPECTED_ASSET_SIZES = {
    "StoreLogo.png": (50, 50),
    "Square44x44Logo.png": (44, 44),
    "Square71x71Logo.png": (71, 71),
    "Square150x150Logo.png": (150, 150),
    "Wide310x150Logo.png": (310, 150),
    "Square310x310Logo.png": (310, 310),
    "StoreListingLogo.png": (300, 300),
}
IDENTITY_PLACEHOLDERS = {
    "__IDENTITY_NAME__",
    "__PUBLISHER__",
    "__PUBLISHER_DISPLAY_NAME__",
    "__VERSION__",
}


def add_error(errors: list[str], message: str) -> None:
    errors.append(message)


def png_dimensions(path: Path) -> tuple[int, int]:
    with path.open("rb") as handle:
        header = handle.read(24)
    if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n" or header[12:16] != b"IHDR":
        raise ValueError("not a valid PNG")
    return struct.unpack(">II", header[16:24])


def check_manifest(errors: list[str]) -> None:
    if not MANIFEST_PATH.exists():
        add_error(errors, f"Missing MSIX manifest template: {MANIFEST_PATH}")
        return

    manifest_text = MANIFEST_PATH.read_text(encoding="utf-8")
    for placeholder in IDENTITY_PLACEHOLDERS:
        if manifest_text.count(placeholder) != 1:
            add_error(errors, f"Manifest must contain {placeholder} exactly once.")

    try:
        root = ET.fromstring(manifest_text)
    except ET.ParseError as exc:
        add_error(errors, f"Manifest XML is invalid: {exc}")
        return

    identity = root.find(f"{{{FOUNDATION_NS}}}Identity")
    if identity is None:
        add_error(errors, "Manifest is missing Identity.")
    else:
        expected_identity = {
            "Name": "__IDENTITY_NAME__",
            "Publisher": "__PUBLISHER__",
            "Version": "__VERSION__",
            "ProcessorArchitecture": "x64",
        }
        for attribute, expected in expected_identity.items():
            if identity.get(attribute) != expected:
                add_error(errors, f"Identity {attribute} must be {expected!r}.")

    target = root.find(
        f"{{{FOUNDATION_NS}}}Dependencies/{{{FOUNDATION_NS}}}TargetDeviceFamily"
    )
    if target is None:
        add_error(errors, "Manifest is missing TargetDeviceFamily.")
    elif target.get("Name") != "Windows.Desktop":
        add_error(errors, "TargetDeviceFamily must be Windows.Desktop.")

    application = root.find(
        f"{{{FOUNDATION_NS}}}Applications/{{{FOUNDATION_NS}}}Application"
    )
    if application is None:
        add_error(errors, "Manifest is missing its desktop Application entry.")
    else:
        if application.get("Executable") != r"DiskWiseAI\DiskWiseAI.exe":
            add_error(errors, "Manifest executable must target DiskWiseAI\\DiskWiseAI.exe.")
        if application.get("EntryPoint") != "Windows.FullTrustApplication":
            add_error(errors, "Desktop entry point must be Windows.FullTrustApplication.")

    capability_parent = root.find(f"{{{FOUNDATION_NS}}}Capabilities")
    capabilities: set[tuple[str, str]] = set()
    if capability_parent is not None:
        for capability in capability_parent:
            namespace = capability.tag.removeprefix("{").split("}", 1)[0]
            capabilities.add((namespace, capability.get("Name", "")))
    expected_capabilities = {
        (FOUNDATION_NS, "internetClient"),
        (RESCAP_NS, "runFullTrust"),
    }
    if capabilities != expected_capabilities:
        add_error(
            errors,
            "Manifest capabilities must be exactly internetClient and restricted runFullTrust.",
        )

    if set(root.get("IgnorableNamespaces", "").split()) != {"uap", "rescap"}:
        add_error(errors, "Manifest IgnorableNamespaces must contain only uap and rescap.")

    visual = root.find(
        f"{{{FOUNDATION_NS}}}Applications/{{{FOUNDATION_NS}}}Application/"
        f"{{{UAP_NS}}}VisualElements"
    )
    if visual is None:
        add_error(errors, "Manifest is missing uap:VisualElements.")
    else:
        for attribute in ("Square150x150Logo", "Square44x44Logo"):
            referenced = visual.get(attribute, "").replace("\\", "/")
            if not referenced or not (ROOT / "packaging" / "msix" / referenced).exists():
                add_error(errors, f"Manifest asset reference {attribute} is missing.")


def check_assets(errors: list[str]) -> int:
    checked = 0
    for name, expected_size in EXPECTED_ASSET_SIZES.items():
        path = ASSETS_DIR / name
        if not path.exists():
            add_error(errors, f"Missing Store asset: {path}")
            continue
        try:
            actual_size = png_dimensions(path)
        except (OSError, ValueError) as exc:
            add_error(errors, f"Could not inspect {path}: {exc}")
            continue
        if actual_size != expected_size:
            add_error(errors, f"{name} is {actual_size}, expected {expected_size}.")
        checked += 1
    return checked


def check_screenshots(errors: list[str]) -> int:
    screenshots = sorted(SCREENSHOTS_DIR.glob("*.png"))
    if len(screenshots) < 4:
        add_error(errors, "At least four Store screenshots are required.")
    for path in screenshots:
        try:
            width, height = png_dimensions(path)
        except (OSError, ValueError) as exc:
            add_error(errors, f"Could not inspect {path}: {exc}")
            continue
        if width < 1366 or height < 768:
            add_error(errors, f"{path.name} is {width}x{height}; minimum is 1366x768.")
    return len(screenshots)


def section_body(markdown: str, heading: str) -> str:
    match = re.search(
        rf"^## {re.escape(heading)}\s*$\n(.*?)(?=^## |\Z)",
        markdown,
        flags=re.IGNORECASE | re.MULTILINE | re.DOTALL,
    )
    return match.group(1).strip() if match else ""


def require_phrases(errors: list[str], path: Path, phrases: tuple[str, ...]) -> str:
    if not path.exists():
        add_error(errors, f"Missing release document: {path}")
        return ""
    text = path.read_text(encoding="utf-8")
    lower_text = text.lower()
    for phrase in phrases:
        if phrase.lower() not in lower_text:
            add_error(errors, f"{path.name} must disclose {phrase!r}.")
    return text


def check_release_metadata(errors: list[str]) -> None:
    listing = require_phrases(
        errors,
        LISTING_PATH,
        (
            "live generative AI",
            "OpenRouter",
            "Recycle Bin",
            "Strict local mode",
            "AI output reporting",
        ),
    )
    search_terms = [
        term.strip().lower()
        for term in section_body(listing, "Search Terms").split(",")
        if term.strip()
    ]
    if not search_terms:
        add_error(errors, "Store listing Search Terms are missing.")
    elif len(search_terms) > 7:
        add_error(errors, "Store listing must not contain more than seven search terms.")
    elif len(search_terms) != len(set(search_terms)):
        add_error(errors, "Store listing search terms must be unique.")

    require_phrases(
        errors,
        PRIVACY_PATH,
        (
            "file names",
            "file paths",
            "file contents",
            "OpenRouter",
            "DPAPI",
            "diagnostic logs",
            "clear diagnostic logs",
            "Contact",
        ),
    )
    require_phrases(
        errors,
        CERTIFICATION_NOTES_PATH,
        (
            "No account or login is required",
            "Mock",
            "runFullTrust",
            "internetClient",
            "Review and Protected",
        ),
    )

    for path in (LISTING_PATH, PRIVACY_PATH):
        if path.exists() and "https://github.com/aminul29/disk-cleanup" not in path.read_text(
            encoding="utf-8"
        ):
            add_error(errors, f"{path.name} is missing the public support repository URL.")


def check_version_alignment(errors: list[str]) -> None:
    constants = (ROOT / "app" / "constants.py").read_text(encoding="utf-8")
    build_script = (ROOT / "scripts" / "build-msix.ps1").read_text(encoding="utf-8")
    app_match = re.search(r'^APP_VERSION\s*=\s*"(\d+\.\d+\.\d+)"', constants, re.MULTILINE)
    package_match = re.search(
        r'\[string\]\$Version\s*=\s*"(\d+\.\d+\.\d+\.\d+)"',
        build_script,
    )
    if not app_match or not package_match:
        add_error(errors, "Could not determine app and default MSIX versions.")
        return
    if package_match.group(1) != f"{app_match.group(1)}.0":
        add_error(
            errors,
            f"Default MSIX version {package_match.group(1)} does not match app version "
            f"{app_match.group(1)}.",
        )


def file_contains(path: Path, needle: bytes) -> bool:
    overlap = max(len(needle) - 1, 0)
    previous = b""
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            payload = previous + chunk
            if needle in payload:
                return True
            previous = payload[-overlap:] if overlap else b""
    return False


def check_release_build(errors: list[str]) -> int:
    executable = DIST_DIR / "DiskWiseAI.exe"
    if not executable.exists():
        add_error(errors, f"Release executable is missing: {executable}")
        return 0

    files = [path for path in DIST_DIR.rglob("*") if path.is_file()]
    forbidden_suffixes = {".db", ".sqlite", ".sqlite3", ".pem", ".pfx", ".key"}
    allowed_data_files = {Path("_internal/lucide/data/lucide-icons.db")}
    for path in files:
        lower_name = path.name.lower()
        relative_path = path.relative_to(DIST_DIR)
        if (
            path.suffix.lower() in forbidden_suffixes
            and relative_path not in allowed_data_files
        ) or lower_name == ".env":
            add_error(errors, f"Private or mutable data file found in release build: {path}")
        try:
            if file_contains(path, b"sk-or-"):
                add_error(errors, f"Possible OpenRouter secret found in release build: {path}")
        except OSError as exc:
            add_error(errors, f"Could not scan release file {path}: {exc}")
    return len(files)


def validate(require_build: bool) -> tuple[list[str], dict[str, int]]:
    errors: list[str] = []
    check_manifest(errors)
    asset_count = check_assets(errors)
    screenshot_count = check_screenshots(errors)
    check_release_metadata(errors)
    check_version_alignment(errors)
    build_file_count = check_release_build(errors) if require_build else 0
    return errors, {
        "assets": asset_count,
        "screenshots": screenshot_count,
        "build_files": build_file_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DiskWise Microsoft Store release inputs.")
    parser.add_argument(
        "--require-build",
        action="store_true",
        help="Also require and inspect the PyInstaller release directory.",
    )
    args = parser.parse_args()

    errors, counts = validate(args.require_build)
    if errors:
        print("Microsoft Store readiness validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    build_note = (
        f", {counts['build_files']} packaged files scanned" if args.require_build else ""
    )
    print(
        "Microsoft Store readiness validation passed: "
        f"{counts['assets']} assets, {counts['screenshots']} screenshots{build_note}."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

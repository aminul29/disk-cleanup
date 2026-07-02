# DiskWise AI

DiskWise AI is a lightweight Windows desktop MVP for local-first disk cleanup. It is built with Python, PySide6, SQLite, psutil, platformdirs, pydantic, and send2trash.

The app scans common user-level locations, classifies findings by risk, previews cleanup, and deletes only user-approved Safe items. Review and Protected items are never cleaned by the MVP.

## Tech Stack

- Python 3.12
- PySide6 for desktop UI
- SQLite for local reports and settings
- psutil for disk usage
- platformdirs for app data paths
- pydantic for typed models
- PyInstaller for later executable packaging
- pytest for safety and persistence tests
- send2trash for recycle-bin deletion where possible

No Rust, Visual Studio, .NET SDK, Windows App SDK, or MSIX tooling is required for MVP development.

## Run Locally

```powershell
uv venv --python 3.12 .venv
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

If you use a standard Python install instead of uv:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

## Test

```powershell
.\scripts\test.ps1
```

## Build Prep

Packaging is still a later milestone. For development, a PyInstaller one-folder build script is available:

```powershell
.\scripts\build.ps1
```

The build output is written to `dist\DiskWiseAI\DiskWiseAI.exe`.

For release distribution, MSIX is the recommended target because it is better aligned with Microsoft Store delivery, app identity, updates, and Windows integration.

## Current MVP Features

- Dashboard with disk usage, reclaimable space, last scan, and AI-style local summary.
- Dashboard restores the latest saved scan and cleanup report after restart.
- Single-instance startup guard.
- Local rotating log file in the app log directory.
- Sidebar navigation: Dashboard, Smart Scan, Results, Large Files, Duplicates, Reports, Settings.
- Quick scan for user temp files, browser cache, thumbnail cache, user app cache, Downloads review candidates, large files, and duplicate candidates.
- Risk classification: Safe, Review, Protected.
- Cleanup preview with explicit confirmation.
- Safe cleanup only.
- Cleanup reports stored in SQLite.
- Scan sessions stored in SQLite and visible in Reports.
- Settings for theme, privacy mode, exclusions, diagnostics placeholder, reset settings, and separate history clearing.
- Mock AI and OpenRouter AI advisor providers.
- Results page AI advice panel with structured safe plan, review priorities, warnings, and confidence.
- License and pricing placeholders.

## Safety Philosophy

DiskWise AI scans locally, classifies conservatively, explains clearly, and cleans only after user approval.

Hard rules:

- Review and Protected items are never deleted.
- Safe items are the only items selected by default.
- Cleanup is previewed before execution.
- System folders, Program Files, registry, and admin-only areas are outside MVP cleanup scope.
- No file names, paths, or contents are uploaded.
- OpenRouter AI receives aggregate scan totals and category summaries only when explicitly configured.

## Future Milestones

MSIX packaging, payment, backend licensing, and OpenRouter-backed summaries are intentionally deferred.

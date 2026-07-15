# DiskWise AI

DiskWise AI is a local-first Windows disk cleanup and storage-review app built with Python 3.12, PySide6, SQLite, psutil, pydantic, platformdirs, and send2trash. Windows builds include pywin32 so Send2Trash uses the modern `IFileOperation` Recycle Bin API.

It scans supported user-level locations, classifies findings as Safe, Review, or Protected, previews cleanup, and moves only selected Safe files to the Windows Recycle Bin. Review and Protected files are never cleaned.

## Core Features

- Dashboard with disk usage, scan state, and latest local report.
- Quick Scan for temporary files and known browser, thumbnail, and app caches.
- Deep Scan for Quick Scan locations plus Downloads review, large files, and duplicate candidates.
- Cleanup preview, explicit confirmation, progress, cancellation, and Recycle Bin cleanup.
- Local SQLite scan history, cleanup reports, exclusions, and settings.
- Optional OpenRouter advice using aggregate category totals only.
- Strict local mode that blocks all external AI requests.
- OpenRouter keys encrypted with Windows DPAPI; no key is included in source or builds.
- Light, dark, and Windows system themes.

## Safety Rules

- Safe items are selected by default and revalidated immediately before cleanup.
- Review items require manual inspection and are never deleted by DiskWise.
- Protected items cannot be selected or deleted.
- System folders, Program Files, source repositories, password-manager data, and personal folders are excluded from automatic cleanup.
- Scanning stays local. File names, paths, and contents are never sent to an AI provider.

See [cleanup-rules.md](app/docs/cleanup-rules.md) and [privacy-policy.md](app/docs/privacy-policy.md).

## Run Locally

```powershell
uv venv --python 3.12 .venv
uv pip install --python .\.venv\Scripts\python.exe -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

With a standard Python installation:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m app.main
```

Rust, Visual Studio, .NET, WinUI, and the Windows App SDK are not required.

## Test

```powershell
.\scripts\test.ps1
```

## Build Windows App

Create the tested PyInstaller one-folder build:

```powershell
.\scripts\build.ps1
```

Output: `dist\DiskWiseAI\DiskWiseAI.exe`

## Build Microsoft Store MSIX

Install the Windows 10 or 11 SDK with MSIX Packaging Tools and Windows App Certification Kit. Then reserve the app name in Partner Center and use the exact package identity values shown there:

```powershell
.\scripts\build-msix.ps1 `
  -IdentityName "PARTNER_CENTER_IDENTITY_NAME" `
  -Publisher "CN=PARTNER_CENTER_PUBLISHER" `
  -PublisherDisplayName "YOUR_PUBLISHER_NAME" `
  -Version "0.1.0.0"
```

The Store signs the uploaded MSIX. Validate it before submission:

```powershell
.\scripts\run-wack.ps1 -PackagePath .\dist\msix\DiskWiseAI_0.1.0.0_x64.msix
```

Submission copy, privacy details, and release gates are in [store-listing.md](app/docs/store-listing.md) and [store-submission-checklist.md](app/docs/store-submission-checklist.md).

Generate privacy-safe Store screenshots from the production UI using isolated demo data:

```powershell
.\.venv\Scripts\python.exe .\scripts\capture-store-screenshots.py
```

Output: `packaging\store\screenshots\*.png`. The capture process does not read or display the user's saved scans, paths, API key, or disk statistics.

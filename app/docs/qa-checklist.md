# QA Checklist

## Startup

- App starts from `scripts/run.ps1`.
- Second launch shows that DiskWise AI is already running.
- SQLite initialization errors show a friendly startup error.
- A local log file is written under the DiskWise AI app log directory.

## Scan

- Quick Scan shows four cache/temp stages and excludes Deep-only analysis.
- Deep Scan includes Downloads review, large files, and duplicate candidates.
- Scan can be cancelled without crashing.
- Safe, Review, and Protected totals are shown after scan.
- Access-denied files are skipped and logged.
- Multiple Chromium browser profiles are discovered.
- Nested cache roots and overlapping Downloads findings are not double-counted.

## Results And Cleanup

- Safe items are selected by default.
- Review items are visible but not selected for cleanup.
- Protected items are never selectable for cleanup.
- Cleanup preview appears before deletion.
- Category selection includes Safe items beyond the first 1,000 displayed rows.
- Cleanup runs in the background with progress and cancellation.
- Accessible files move to the Recycle Bin; no permanent-delete fallback is used.
- After a live scan, Dashboard actions remain enabled and **Clean Safe Items** opens the cleanup preview.
- The packaged app log reports `Recycle Bin backend: Windows IFileOperation`.
- Locked, missing, and policy-blocked files remain in place and are reported.
- Cleanup report is created after cleanup.

## Reports

- Cleanup reports list correctly.
- Report details open.
- Copy Summary works.
- Scan Sessions list saved scans.
- Reports include duration, free-space before/after, mode, cancellation, and issues.

## Settings

- Excluded folders must exist.
- Duplicate exclusions are blocked.
- Scan history can be cleared separately.
- Cleanup reports can be cleared separately.
- Reset Settings restores default preferences.
- OpenRouter keys migrate from plaintext and are encrypted with Windows DPAPI.
- The welcome tour can be reopened.

## Privacy

- No file names, paths, or contents are uploaded.
- Mock AI works locally.
- Strict local mode blocks OpenRouter.
- OpenRouter payloads contain aggregate category data only and omit scan identifiers.
- AI output reporting opens the support issue form without attaching scan data.

## Packaging Prep

- `scripts/test.ps1` passes.
- `scripts/build.ps1` produces a PyInstaller one-folder build.
- Built app starts and can scan without admin privileges.
- `scripts/build-msix.ps1` renders Partner Center identity values and creates an MSIX.
- Windows App Certification Kit passes for the final MSIX.

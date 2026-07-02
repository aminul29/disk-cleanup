# QA Checklist

## Startup

- App starts from `scripts/run.ps1`.
- Second launch shows that DiskWise AI is already running.
- SQLite initialization errors show a friendly startup error.
- A local log file is written under the DiskWise AI app log directory.

## Scan

- Quick scan shows staged progress.
- Scan can be cancelled without crashing.
- Safe, Review, and Protected totals are shown after scan.
- Access-denied files are skipped and logged.

## Results And Cleanup

- Safe items are selected by default.
- Review items are visible but not selected for cleanup.
- Protected items are never selectable for cleanup.
- Cleanup preview appears before deletion.
- Cleanup report is created after cleanup.

## Reports

- Cleanup reports list correctly.
- Report details open.
- Copy Summary works.
- Scan Sessions list saved scans.

## Settings

- Excluded folders must exist.
- Duplicate exclusions are blocked.
- Scan history can be cleared separately.
- Cleanup reports can be cleared separately.
- Reset Settings restores default preferences.

## Privacy

- No file names, paths, or contents are uploaded.
- AI summary remains local/mock-only.
- Diagnostics setting is a placeholder only.

## Packaging Prep

- `scripts/test.ps1` passes.
- `scripts/build.ps1` produces a PyInstaller one-folder build.
- Built app starts and can scan without admin privileges.

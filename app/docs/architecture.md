# DiskWise AI Architecture

## Overview

DiskWise AI is a local Python desktop app with a modular service layer so scanning, cleanup, AI summaries, licensing, and persistence can be replaced later.

```text
app/
  main.py
  ui/
  services/
  models/
  database/
  utils/
  docs/
```

## Data Flow

1. `ScanPage` starts a background `ScanWorker`.
2. `ScanService` scans local folders and returns a `ScanResult`.
3. `ReportService` stores scan summary data in SQLite.
4. UI pages render categories, large files, and duplicate groups.
5. `ResultsPage` builds a cleanup preview from selected Safe items.
6. `CleanupService` validates risk and safe paths again before deletion.
7. `ReportService` stores cleanup reports in SQLite.
8. `ReportsPage` displays cleanup report details and previous scan sessions from SQLite.
9. `DashboardPage` reads the latest saved scan/report on startup so the app is useful across sessions.

## Replaceable Services

- `ScanService`: can later be replaced by Rust, C#, or a more advanced scanner.
- `AiAdvisorService`: provides Mock and OpenRouter AI advice using privacy-safe aggregate scan data.
- `MockLicenseService`: can later call a licensing backend.
- `CleanupService`: keeps deletion safety rules centralized.
- `app.utils.safety`: keeps protected-path and safe-root decisions deterministic and testable.
- `LocalDatabase`: stores settings, scan summaries, exclusions, and reports.

## Local Data

SQLite is stored under the OS app data directory using `platformdirs`.

The MVP stores summary data by default and uses scan details in memory for the active session.

## Runtime Reliability

- `app.runtime.configure_logging` writes a rotating local log file.
- `app.runtime.SingleInstanceGuard` prevents duplicate app windows.
- Startup initialization is wrapped with a friendly error dialog if local services fail.

## AI Boundary

AI can explain, prioritize, and recommend cleanup review steps. AI cannot authorize deletion. `CleanupService` still enforces deterministic Safe-only cleanup rules.

AI output is rendered as structured advice in Dashboard and Results. Results uses safe cleanup plan, review priorities, warnings, and confidence fields when the provider returns them.

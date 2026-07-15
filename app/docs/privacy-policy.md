# DiskWise AI Privacy Policy

Effective date: July 15, 2026

DiskWise AI is a local-first Windows storage cleanup application. This policy explains what the app processes and when information may leave your device.

## Local File Processing

DiskWise scans supported folders on your Windows device to calculate file sizes, dates, categories, and cleanup risk. File names and paths may be displayed inside the app so you can review results. File contents are read only when Deep Scan hashes duplicate candidates locally.

DiskWise does not upload file names, file paths, or file contents. Cleanup is performed locally and only selected Safe files are eligible to be moved to the Windows Recycle Bin.

## Data Stored on Your Device

DiskWise stores the following locally:

- Aggregate scan history and scan errors.
- Cleanup reports and cleanup errors.
- Theme, privacy, AI provider, model, exclusion, and onboarding settings.
- An optional OpenRouter API key encrypted with Windows Data Protection API (DPAPI) for your Windows account.
- Rotating diagnostic logs needed to troubleshoot the app. Cleanup action logs use generated item identifiers instead of file paths.

You can clear scan history and cleanup reports from Settings. You can remove an API key by clearing it and saving AI settings.

## Optional OpenRouter AI

OpenRouter integration is optional and disabled from external access while Strict local mode is enabled. When you select OpenRouter, turn off Strict local mode, and request AI advice, DiskWise sends only aggregate scan totals and category summaries. This can include byte counts, item counts, category names, risk levels, and error counts. It does not include file names, paths, contents, scan identifiers, or duplicate hashes.

Requests go directly from your device to OpenRouter using the API key you provide. OpenRouter may process network information such as your IP address and account usage under its own terms and privacy policy. DiskWise does not receive or store your OpenRouter account information.

## Collection, Sale, and Advertising

DiskWise does not include analytics or advertising, does not sell personal data, and does not send diagnostic telemetry to the developer.

## AI Output and Safety

AI output is advisory. It cannot authorize cleanup or override DiskWise safety classifications. Review and Protected files are never cleaned. You can report problematic AI output through the in-app reporting link, which opens the DiskWise GitHub issue form without automatically attaching scan data.

## Children

DiskWise is a general-purpose utility and is not directed to children under 13.

## Changes

Material changes to this policy will be published with an updated effective date before a new app release.

## Contact

For privacy questions or support, open an issue at https://github.com/aminul29/disk-cleanup/issues. Do not include private file names, paths, API keys, or file contents in a support request.

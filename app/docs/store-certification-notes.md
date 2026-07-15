# Microsoft Store Certification Notes Draft

## Test Access

No account or login is required. DiskWise AI is fully testable without a network connection, payment, license key, or OpenRouter API key.

## Suggested Notes For Certification

DiskWise AI is a local-first desktop storage utility. On first launch, complete the welcome tour and choose Quick Scan. A scan reads supported user-level temporary and cache locations and then opens Results automatically.

Safe findings are selected by default. Select **Preview Cleanup** to inspect the exact plan. Cleanup requires an explicit confirmation checkbox and moves only selected Safe files to the Windows Recycle Bin. Review and Protected findings cannot be cleaned by the app.

The default AI provider is **Mock**, which produces local deterministic advice and requires no external service. Optional live generative AI advice through OpenRouter is only available after the tester selects OpenRouter, provides their own key, turns off Strict local mode, saves the settings, and requests advice. No OpenRouter credentials are required to certify the core product.

The **Report AI Output** command opens the public support issue form without attaching scan data. The in-app Settings page links to the public privacy policy and support page.

## Capability Justification

- `runFullTrust`: required for this PySide6 desktop app to inspect supported user-level folders, read local file metadata, maintain local SQLite reports, and move confirmed Safe files to the Windows Recycle Bin.
- `internetClient`: used only for optional OpenRouter advice and user-initiated support, privacy, and AI-reporting links. Scanning and cleanup do not require network access.

## Important Product Limits

- DiskWise never cleans Review or Protected findings.
- Duplicate and large-file views are review-only in this release.
- Files moved to the Recycle Bin continue using disk space until the user empties the Recycle Bin.
- Locked or inaccessible files are skipped and reported instead of being permanently deleted.

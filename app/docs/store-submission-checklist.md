# Microsoft Store Submission Checklist

## Partner Center Inputs

- [ ] Reserve `DiskWise AI` in Partner Center.
- [ ] Copy the exact package Identity Name, Publisher, and Publisher Display Name into the MSIX build command.
- [ ] Confirm the publisher/support contact shown in the listing.
- [ ] Publish the privacy policy at a stable public URL.
- [ ] Complete age ratings and generative-AI declarations accurately.

## Build And Validation

- [ ] Run `scripts\test.ps1` successfully.
- [ ] Run `scripts\build.ps1` and smoke-test `dist\DiskWiseAI\DiskWiseAI.exe`.
- [ ] Run `.\.venv\Scripts\python.exe .\scripts\validate-store-readiness.py --require-build` successfully.
- [ ] Build MSIX with `scripts\build-msix.ps1` and a four-part version higher than the previous submission.
- [ ] Alternatively, run **Build Microsoft Store MSIX** in GitHub Actions with the exact Partner Center values and download its submission bundle.
- [ ] Verify the downloaded MSIX against `SHA256SUMS.txt` before uploading it to Partner Center.
- [ ] Install the package on a clean Windows user account and test launch/uninstall.
- [ ] Optionally run `scripts\run-wack.ps1` when the Windows App Certification Kit is available; Partner Center certification is authoritative.
- [ ] Confirm no API key or user database is present in the staged package.
- [ ] Paste the test flow and capability reasons from `store-certification-notes.md` into Partner Center submission notes.
- [ ] Confirm `internetClient` is declared only for optional OpenRouter requests and `runFullTrust` only for the packaged Win32 desktop process.

## Core Workflow QA

- [ ] Quick Scan completes, cancels safely, and excludes Deep-only stages.
- [ ] Deep Scan finds supported Downloads, large-file, and duplicate candidates.
- [ ] Safe items are selected by default.
- [ ] Review items are not eligible for cleanup.
- [ ] Protected items cannot be selected or cleaned.
- [ ] Cleanup preview totals match selected Safe items.
- [ ] Cleanup moves accessible files to the Recycle Bin and reports locked/skipped files.
- [ ] Dashboard, Results, Large Files, Duplicates, and Reports refresh after scan/cleanup.
- [ ] Scan history and cleanup reports survive restart and clear correctly.
- [ ] Exclusions are honored without suppressing unrelated sibling folders.

## AI And Privacy QA

- [ ] Mock AI works without a network connection.
- [ ] Strict local mode blocks OpenRouter requests.
- [ ] OpenRouter test and advice run off the UI thread.
- [ ] Captured OpenRouter payload contains no file names, paths, contents, scan IDs, or duplicate hashes.
- [ ] API key is encrypted at rest with DPAPI and is absent from logs/build output.
- [ ] The in-app AI reporting link opens without attaching scan data.
- [ ] Clear Diagnostic Logs removes current and rotated logs without clearing scan or cleanup history.

## Listing Assets

- [ ] App logos generated with `scripts\generate-store-assets.py` are visually checked.
- [ ] Regenerate sanitized screenshots with `scripts\capture-store-screenshots.py`.
- [ ] At least four generated screenshots are visually checked at 1366 x 768 or larger.
- [ ] Listing text explains that space is reclaimed after the Recycle Bin is emptied.
- [ ] Support, privacy, and AI reporting links are public and working.

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
- [ ] Build MSIX with `scripts\build-msix.ps1` and a four-part version higher than the previous submission.
- [ ] Install the package on a clean Windows user account and test launch/uninstall.
- [ ] Run `scripts\run-wack.ps1` and resolve all failures.
- [ ] Confirm no API key or user database is present in the staged package.

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

## Listing Assets

- [ ] App logos generated with `scripts\generate-store-assets.py` are visually checked.
- [ ] Regenerate sanitized screenshots with `scripts\capture-store-screenshots.py`.
- [ ] At least four generated screenshots are visually checked at 1366 x 768 or larger.
- [ ] Listing text explains that space is reclaimed after the Recycle Bin is emptied.
- [ ] Support, privacy, and AI reporting links are public and working.

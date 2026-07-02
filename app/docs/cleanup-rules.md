# Cleanup Rules

## Risk Levels

- Safe: user-level temp/cache files that can be selected by default.
- Review: files that may be removable but need manual judgment.
- Protected: files or folders that must never be cleaned by the MVP.

## Safe Categories

- User temp files
- App temp files inside user profile
- Browser cache files under accessible user profiles
- Windows thumbnail cache files under the current user profile
- User-level crash dumps and known cache folders

Safe files can be selected by default, but cleanup still requires preview and confirmation.

## Review Categories

- Old downloads
- Large downloads
- Installers, archives, and disk images
- Large files in common user folders
- Duplicate candidates

Review files are not deleted by the MVP.

## Protected Categories

- Documents
- Desktop
- Pictures
- Videos
- Music
- Source code folders
- Password manager data
- Accounting/bookkeeping files
- Windows
- System32
- Program Files
- Program Files (x86)
- WindowsApps
- Registry
- Anything requiring admin permission

Protected files are never selected and never cleaned.

## Deletion Rules

1. Show a preview first.
2. Require confirmation.
3. Validate that every item is Safe.
4. Validate that every path is inside a known temp/cache root.
5. Reject protected folders even when they are nested inside a safe root.
6. Prefer recycle-bin deletion through `send2trash`.
7. Log cleanup results to SQLite.
8. Skip failures and continue safely.

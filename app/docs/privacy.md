# Privacy Engineering Notes

DiskWise AI is local-first by design.

- Scanning and cleanup run on the user's Windows device.
- File names, paths, and contents are never included in AI requests.
- Scan history and cleanup reports are stored in local SQLite.
- Cleanup logs use generated item IDs and categories instead of file paths.
- OpenRouter is optional. Requests contain aggregate byte counts, item counts, category labels, and safety classifications only.
- Strict local mode blocks all OpenRouter requests.
- OpenRouter API keys are encrypted with Windows DPAPI for the current Windows account or read from `OPENROUTER_API_KEY`.
- DiskWise includes no analytics, advertising, telemetry, payment, or developer-owned API key.
- Users can clear scan history, cleanup reports, and rotating diagnostic logs independently from Settings.

The customer-facing policy is [privacy-policy.md](privacy-policy.md).

# Privacy

DiskWise AI is local-first.

In this MVP:

- No file names are uploaded.
- No file paths are uploaded.
- No file contents are uploaded.
- External AI is optional and disabled by default.
- When OpenRouter is enabled, DiskWise sends aggregate scan totals and category summaries only.
- OpenRouter API keys are never hardcoded. Users can store a local key in Settings or use `OPENROUTER_API_KEY`.
- Scan summaries and cleanup reports stay in local SQLite.
- Users can clear local history from Settings.

Future AI features should call a backend service. The backend may call external providers, but the Windows client must remain an untrusted client and must not contain provider keys or business secrets.

from __future__ import annotations

from pathlib import Path

from app.database.local_database import LocalDatabase


class SettingsService:
    def __init__(self, database: LocalDatabase) -> None:
        self.database = database
        if self.database.get_setting("privacy_mode", None) is None:
            self.database.set_setting("privacy_mode", True)
        if self.database.get_setting("theme", None) is None:
            self.database.set_setting("theme", "System")
        if self.database.get_setting("ai_provider", None) is None:
            self.database.set_setting("ai_provider", "Mock")
        if self.database.get_setting("openrouter_model", None) is None:
            self.database.set_setting("openrouter_model", "openai/gpt-4.1-mini")

    def get_theme(self) -> str:
        return str(self.database.get_setting("theme", "System"))

    def set_theme(self, theme: str) -> None:
        self.database.set_setting("theme", theme)

    def privacy_mode_enabled(self) -> bool:
        return bool(self.database.get_setting("privacy_mode", True))

    def set_privacy_mode(self, enabled: bool) -> None:
        self.database.set_setting("privacy_mode", enabled)

    def ai_summary_enabled(self) -> bool:
        return bool(self.database.get_setting("ai_summary", True))

    def set_ai_summary_enabled(self, enabled: bool) -> None:
        self.database.set_setting("ai_summary", enabled)

    def get_ai_provider(self) -> str:
        return str(self.database.get_setting("ai_provider", "Mock"))

    def set_ai_provider(self, provider: str) -> None:
        self.database.set_setting("ai_provider", provider)

    def get_openrouter_api_key(self) -> str:
        return str(self.database.get_setting("openrouter_api_key", ""))

    def set_openrouter_api_key(self, api_key: str) -> None:
        self.database.set_setting("openrouter_api_key", api_key.strip())

    def get_openrouter_model(self) -> str:
        return str(self.database.get_setting("openrouter_model", "openai/gpt-4.1-mini"))

    def set_openrouter_model(self, model: str) -> None:
        self.database.set_setting("openrouter_model", model.strip())

    def diagnostics_enabled(self) -> bool:
        return bool(self.database.get_setting("diagnostics", False))

    def set_diagnostics_enabled(self, enabled: bool) -> None:
        self.database.set_setting("diagnostics", enabled)

    def get_excluded_folders(self) -> list[Path]:
        with self.database.connect() as connection:
            rows = connection.execute("SELECT path FROM excluded_folders ORDER BY path").fetchall()
        return [Path(row["path"]) for row in rows]

    def add_excluded_folder(self, path: Path) -> None:
        resolved = path.resolve()
        with self.database.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO excluded_folders (path) VALUES (?)",
                (str(resolved),),
            )

    def remove_excluded_folder(self, path: Path) -> None:
        with self.database.connect() as connection:
            connection.execute("DELETE FROM excluded_folders WHERE path = ?", (str(path),))

    def clear_history(self) -> None:
        self.database.clear_history()

    def clear_scan_history(self) -> None:
        self.database.clear_scan_history()

    def clear_cleanup_reports(self) -> None:
        self.database.clear_cleanup_reports()

    def reset_settings(self) -> None:
        self.database.reset_settings()
        self.database.set_setting("privacy_mode", True)
        self.database.set_setting("theme", "System")
        self.database.set_setting("ai_summary", True)
        self.database.set_setting("diagnostics", False)
        self.database.set_setting("ai_provider", "Mock")
        self.database.set_setting("openrouter_model", "openai/gpt-4.1-mini")

from __future__ import annotations

from pathlib import Path
import logging

from app.database.local_database import LocalDatabase
from app.runtime import clear_diagnostic_logs
from app.utils.secret_store import protect_secret, unprotect_secret


class SettingsService:
    def __init__(self, database: LocalDatabase) -> None:
        self.database = database
        self.logger = logging.getLogger(__name__)
        if self.database.get_setting("privacy_mode", None) is None:
            self.database.set_setting("privacy_mode", True)
        if self.database.get_setting("theme", None) is None:
            self.database.set_setting("theme", "System")
        if self.database.get_setting("ai_provider", None) is None:
            self.database.set_setting("ai_provider", "Mock")
        if self.database.get_setting("openrouter_model", None) is None:
            self.database.set_setting("openrouter_model", "openai/gpt-4.1-mini")
        if self.database.get_setting("scan_mode", None) is None:
            self.database.set_setting("scan_mode", "Quick")
        if self.database.get_setting("onboarding_completed", None) is None:
            self.database.set_setting("onboarding_completed", False)

    def get_theme(self) -> str:
        return str(self.database.get_setting("theme", "System"))

    def set_theme(self, theme: str) -> None:
        self.database.set_setting("theme", theme)

    def get_scan_mode(self) -> str:
        return str(self.database.get_setting("scan_mode", "Quick"))

    def set_scan_mode(self, mode: str) -> None:
        self.database.set_setting("scan_mode", "Deep" if mode == "Deep" else "Quick")

    def onboarding_completed(self) -> bool:
        return bool(self.database.get_setting("onboarding_completed", False))

    def set_onboarding_completed(self, completed: bool) -> None:
        self.database.set_setting("onboarding_completed", completed)

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
        protected = str(self.database.get_setting("openrouter_api_key_secure", ""))
        if protected:
            try:
                return unprotect_secret(protected)
            except (OSError, ValueError) as exc:
                self.logger.warning("Could not decrypt the saved OpenRouter key: %s", exc)
                return ""

        legacy = str(self.database.get_setting("openrouter_api_key", ""))
        if legacy:
            self.set_openrouter_api_key(legacy)
            return legacy.strip()
        return ""

    def set_openrouter_api_key(self, api_key: str) -> None:
        cleaned = api_key.strip()
        self.database.set_setting(
            "openrouter_api_key_secure",
            protect_secret(cleaned) if cleaned else "",
        )
        self.database.delete_setting("openrouter_api_key")

    def get_openrouter_model(self) -> str:
        return str(self.database.get_setting("openrouter_model", "openai/gpt-4.1-mini"))

    def set_openrouter_model(self, model: str) -> None:
        self.database.set_setting("openrouter_model", model.strip())

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

    def clear_diagnostic_logs(self) -> None:
        clear_diagnostic_logs()

    def reset_settings(self) -> None:
        self.database.reset_settings()
        self.database.set_setting("privacy_mode", True)
        self.database.set_setting("theme", "System")
        self.database.set_setting("ai_summary", True)
        self.database.set_setting("ai_provider", "Mock")
        self.database.set_setting("openrouter_model", "openai/gpt-4.1-mini")
        self.database.set_setting("scan_mode", "Quick")

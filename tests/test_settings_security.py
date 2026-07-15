from __future__ import annotations

from pathlib import Path

from app.database.local_database import LocalDatabase
from app.services.settings_service import SettingsService


def make_settings(tmp_path: Path) -> tuple[LocalDatabase, SettingsService]:
    database = LocalDatabase(tmp_path / "settings.db")
    database.initialize()
    return database, SettingsService(database)


def test_openrouter_key_is_encrypted_at_rest(tmp_path: Path) -> None:
    database, settings = make_settings(tmp_path)
    api_key = "sk-or-diskwise-test-key"

    settings.set_openrouter_api_key(api_key)

    stored = database.get_setting("openrouter_api_key_secure", "")
    assert stored.startswith("dpapi:")
    assert api_key not in stored
    assert settings.get_openrouter_api_key() == api_key
    assert database.get_setting("openrouter_api_key", None) is None


def test_plaintext_legacy_key_is_migrated_on_read(tmp_path: Path) -> None:
    database, settings = make_settings(tmp_path)
    api_key = "legacy-test-key"
    database.set_setting("openrouter_api_key", api_key)

    assert settings.get_openrouter_api_key() == api_key
    assert database.get_setting("openrouter_api_key", None) is None
    assert database.get_setting("openrouter_api_key_secure", "").startswith("dpapi:")

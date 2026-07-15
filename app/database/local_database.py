from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator


class LocalDatabase:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS scan_history (
                    scan_id TEXT PRIMARY KEY,
                    started_at TEXT NOT NULL,
                    completed_at TEXT,
                    duration_seconds REAL NOT NULL,
                    total_files_scanned INTEGER NOT NULL,
                    total_bytes_scanned INTEGER NOT NULL,
                    safe_bytes INTEGER NOT NULL,
                    review_bytes INTEGER NOT NULL,
                    protected_bytes INTEGER NOT NULL,
                    summary_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS cleanup_reports (
                    report_id TEXT PRIMARY KEY,
                    scan_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    files_deleted INTEGER NOT NULL,
                    files_skipped INTEGER NOT NULL,
                    bytes_recovered INTEGER NOT NULL,
                    categories_cleaned TEXT NOT NULL,
                    errors TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    duration_seconds REAL NOT NULL DEFAULT 0,
                    free_space_before_bytes INTEGER NOT NULL DEFAULT 0,
                    free_space_after_bytes INTEGER NOT NULL DEFAULT 0,
                    canceled INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS excluded_folders (
                    path TEXT PRIMARY KEY
                );
                """
            )
            self._ensure_columns(
                connection,
                "cleanup_reports",
                {
                    "duration_seconds": "REAL NOT NULL DEFAULT 0",
                    "free_space_before_bytes": "INTEGER NOT NULL DEFAULT 0",
                    "free_space_after_bytes": "INTEGER NOT NULL DEFAULT 0",
                    "canceled": "INTEGER NOT NULL DEFAULT 0",
                },
            )

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA busy_timeout = 10000")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def set_setting(self, key: str, value: Any) -> None:
        payload = json.dumps(value)
        with self.connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, payload),
            )

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.connect() as connection:
            row = connection.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if row is None:
            return default
        try:
            return json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return default

    def delete_setting(self, key: str) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM settings WHERE key = ?", (key,))

    def clear_history(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM scan_history")
            connection.execute("DELETE FROM cleanup_reports")

    def clear_scan_history(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM scan_history")

    def clear_cleanup_reports(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM cleanup_reports")

    def reset_settings(self) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM settings")

    def _ensure_columns(
        self,
        connection: sqlite3.Connection,
        table: str,
        columns: dict[str, str],
    ) -> None:
        existing = {
            str(row["name"])
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        for name, definition in columns.items():
            if name not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {name} {definition}")

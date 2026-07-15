from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from app import runtime


def test_clear_diagnostic_logs_removes_rotated_files_and_keeps_handler_usable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    log_path = tmp_path / "diskwise.log"
    monkeypatch.setattr(runtime, "LOG_PATH", log_path)
    handler = RotatingFileHandler(log_path, maxBytes=1000, backupCount=3, encoding="utf-8")
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    log_path.write_text("current log", encoding="utf-8")
    for index in range(1, 4):
        Path(f"{log_path}.{index}").write_text("rotated log", encoding="utf-8")

    try:
        runtime.clear_diagnostic_logs()

        assert not log_path.exists()
        assert not any(Path(f"{log_path}.{index}").exists() for index in range(1, 4))

        root_logger.warning("logging continues after clear")
        handler.flush()
        assert "logging continues after clear" in log_path.read_text(encoding="utf-8")
    finally:
        root_logger.removeHandler(handler)
        handler.close()

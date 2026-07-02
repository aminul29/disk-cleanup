from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from PySide6.QtNetwork import QLocalServer, QLocalSocket

from app.constants import APP_LOG_DIR, LOG_PATH


def configure_logging() -> None:
    APP_LOG_DIR.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    if root_logger.handlers:
        return

    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=1_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    root_logger.addHandler(file_handler)


class SingleInstanceGuard:
    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        self.server: QLocalServer | None = None

    def is_another_instance_running(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self.server_name)
        if socket.waitForConnected(150):
            socket.disconnectFromServer()
            return True

        QLocalServer.removeServer(self.server_name)
        self.server = QLocalServer()
        if not self.server.listen(self.server_name):
            logging.getLogger(__name__).warning(
                "Could not create single-instance guard: %s",
                self.server.errorString(),
            )
            return False
        return False

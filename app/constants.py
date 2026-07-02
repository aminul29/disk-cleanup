from __future__ import annotations

from pathlib import Path

from platformdirs import user_data_dir, user_log_dir

APP_NAME = "DiskWise AI"
APP_ID = "com.diskwise.diskwiseai"
APP_AUTHOR = "DiskWise"
APP_VERSION = "0.1.0"
APP_DESCRIPTION = "Local-first Windows disk cleanup MVP."

PACKAGE_ROOT = Path(__file__).resolve().parent
ASSETS_DIR = PACKAGE_ROOT / "assets"
APP_ICON_PATH = ASSETS_DIR / "app-icon.svg"

APP_DATA_DIR = Path(user_data_dir("DiskWiseAI", APP_AUTHOR))
APP_LOG_DIR = Path(user_log_dir("DiskWiseAI", APP_AUTHOR))
DATABASE_PATH = APP_DATA_DIR / "diskwise.db"
LOG_PATH = APP_LOG_DIR / "diskwise.log"

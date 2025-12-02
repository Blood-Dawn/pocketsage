"""Application configuration objects and helpers."""

from __future__ import annotations

import os
import importlib
from pathlib import Path
from urllib.parse import quote_plus
from typing import Any

from dotenv import load_dotenv

load_dotenv()


def _env_bool(name: str, default: bool = False) -> bool:
    """Interpret environment variable values as booleans."""

    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class BaseConfig:
    """Base configuration shared across environments."""

    APP_NAME = "PocketSage"
    DB_FILENAME = "pocketsage.db"
    EXPORT_RETENTION = 5
    SQLCIPHER_FLAG = "POCKETSAGE_USE_SQLCIPHER"
    SQLCIPHER_KEY_ENV = "POCKETSAGE_SQLCIPHER_KEY"
    SQLITE_PRAGMAS = {"journal_mode": "wal", "foreign_keys": "on"}

    def __init__(self) -> None:
        self.SECRET_KEY = os.getenv("POCKETSAGE_SECRET_KEY", "replace-me")
        self.DATA_DIR = self._resolve_data_dir()
        self.USE_SQLCIPHER = _env_bool(self.SQLCIPHER_FLAG, default=False)
        self.SQLCIPHER_KEY = os.getenv(self.SQLCIPHER_KEY_ENV)
        self.DEV_MODE = _env_bool("POCKETSAGE_DEV_MODE", default=True)
        self.DATABASE_URL = os.getenv("POCKETSAGE_DATABASE_URL", self._build_sqlite_url())
        if not self.DEV_MODE and self.SECRET_KEY == "replace-me":
            raise ValueError("POCKETSAGE_SECRET_KEY must be set in non-dev mode.")

    def _resolve_data_dir(self) -> Path:
        """Return the directory where SQLite/SQLCipher files live."""

        data_root = os.getenv("POCKETSAGE_DATA_DIR", "instance")
        base_path = Path(data_root).expanduser()
        try:
            path = base_path.resolve()
            path.mkdir(parents=True, exist_ok=True)
            return path
        except PermissionError:
            # If Program Files or other protected locations block writes, fall back to user-local storage.
            local_app_data = os.getenv("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
            fallback_path = Path(local_app_data).expanduser() / self.APP_NAME
            fallback_path.mkdir(parents=True, exist_ok=True)
            return fallback_path.resolve()

    def _ensure_sqlcipher_available(self) -> None:
        """Ensure the SQLCipher driver is available when enabled."""

        if not self.SQLCIPHER_KEY:
            raise ValueError(
                "POCKETSAGE_USE_SQLCIPHER is enabled but POCKETSAGE_SQLCIPHER_KEY is not set."
            )
        try:
            importlib.import_module("sqlcipher3")
        except ImportError as exc:
            raise ImportError(
                "POCKETSAGE_USE_SQLCIPHER=true requires sqlcipher3 (binary wheel). "
                "Install with: pip install sqlcipher3-binary or use the 'sqlcipher' extra."
            ) from exc

    def _build_sqlite_url(self) -> str:
        """Construct the default SQLite URL respecting the SQLCipher toggle."""

        db_path = self.DATA_DIR / self.DB_FILENAME
        if self.USE_SQLCIPHER:
            self._ensure_sqlcipher_available()
            key = quote_plus(self.SQLCIPHER_KEY or "")
            # sqlcipher3 driver; key is applied on connect via PRAGMA key
            return f"sqlite:///{db_path}"
        return f"sqlite:///{db_path}"

    def sqlalchemy_engine_options(self) -> dict[str, Any]:
        """Expose engine kwargs for SQLModel to consume."""

        connect_args: dict[str, Any] = {"check_same_thread": False, "uri": False}
        engine_options: dict[str, Any] = {"connect_args": connect_args}
        if self.USE_SQLCIPHER:
            connect_args["uri"] = True
            connect_args["timeout"] = 30
            engine_options.setdefault("execution_options", {})
        return engine_options


class DevConfig(BaseConfig):
    """Development configuration using local SQLite."""

    DEBUG = True
    TESTING = False
    # TODO(@framework-owner): consider enabling toolbar once UI is wired.

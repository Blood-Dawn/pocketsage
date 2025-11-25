"""Application configuration objects and helpers."""

from __future__ import annotations

import os
from pathlib import Path
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
        self.DEV_MODE = _env_bool("POCKETSAGE_DEV_MODE", default=True)
        self.DATABASE_URL = os.getenv("POCKETSAGE_DATABASE_URL", self._build_sqlite_url())
        # TODO(@security-team): fail fast when SECRET_KEY is default in production modes.

    def _resolve_data_dir(self) -> Path:
        """Return the directory where SQLite/SQLCipher files live."""

        data_root = os.getenv("POCKETSAGE_DATA_DIR", "instance")
        path = Path(data_root).expanduser().resolve()
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _build_sqlite_url(self) -> str:
        """Construct the default SQLite URL respecting the SQLCipher toggle."""

        db_path = self.DATA_DIR / self.DB_FILENAME
        if self.USE_SQLCIPHER:
            # TODO(@security-team): replace with SQLCipher driver URL and pragma
            #   injection once SQLCipher driver is wired into dependencies.
            return f"sqlite:///{db_path}?cipher=sqlcipher"
        return f"sqlite:///{db_path}"

    def sqlalchemy_engine_options(self) -> dict[str, Any]:
        """Expose engine kwargs for SQLModel to consume."""

        connect_args: dict[str, Any] = {"check_same_thread": False, "uri": False}
        engine_options: dict[str, Any] = {"connect_args": connect_args}
        if self.USE_SQLCIPHER:
            connect_args["uri"] = True
            engine_options.setdefault("execution_options", {})
            # TODO(@db-team): add SQLCipher pragma key handshake using env key material.
        return engine_options


class DevConfig(BaseConfig):
    """Development configuration using local SQLite."""

    DEBUG = True
    TESTING = False
    # TODO(@framework-owner): consider enabling toolbar once UI is wired.

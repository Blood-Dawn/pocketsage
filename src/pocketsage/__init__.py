"""PocketSage desktop application package."""

from __future__ import annotations

from .config import BaseConfig, DevConfig
from .desktop.context import create_app_context

__all__ = ["BaseConfig", "DevConfig", "create_app_context"]

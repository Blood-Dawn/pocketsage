"""Small helpers for dev-mode logging and diagnostics."""

from __future__ import annotations

import traceback
from typing import Any, Mapping

from .config import BaseConfig


def in_dev_mode(config: BaseConfig | None) -> bool:
    """Return True when dev mode logging is enabled."""

    return bool(getattr(config, "DEV_MODE", False)) if config is not None else False


def dev_log(
    config: BaseConfig | None,
    message: str,
    *,
    exc: Exception | None = None,
    context: Mapping[str, Any] | None = None,
) -> None:
    """Print developer-friendly diagnostics when dev mode is enabled."""

    if not in_dev_mode(config):
        return

    parts = [f"[DEV] {message}"]
    if context:
        extras = " ".join(f"{k}={v}" for k, v in context.items())
        if extras:
            parts.append(f"({extras})")
    print(" ".join(parts))
    if exc:
        traceback.print_exception(exc)


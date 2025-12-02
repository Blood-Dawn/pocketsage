"""SQLCipher configuration safeguards."""

from __future__ import annotations

import os

import pytest
import importlib
import pocketsage.config as cfg


def test_sqlcipher_requires_key(monkeypatch):
    """Enabling SQLCipher without a key should raise a ValueError."""

    monkeypatch.setenv("POCKETSAGE_USE_SQLCIPHER", "true")
    monkeypatch.delenv("POCKETSAGE_SQLCIPHER_KEY", raising=False)
    with pytest.raises(ValueError):
        cfg.BaseConfig()


def test_sqlcipher_missing_driver(monkeypatch):
    """If SQLCipher is enabled but driver missing, raise ImportError."""

    monkeypatch.setenv("POCKETSAGE_USE_SQLCIPHER", "true")
    monkeypatch.setenv("POCKETSAGE_SQLCIPHER_KEY", "test-key")

    # Force import failure for sqlcipher3
    monkeypatch.setattr(importlib, "import_module", lambda name: (_ for _ in ()).throw(ImportError()) if name == "sqlcipher3" else importlib.import_module(name))

    with pytest.raises(ImportError):
        cfg.BaseConfig()

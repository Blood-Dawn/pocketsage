"""Ledger blueprint package."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "ledger",
    __name__,
    url_prefix="/ledger",
    template_folder="../../templates/ledger",
)

# TODO(@framework-owner): evaluate static_folder usage for blueprint-scoped assets.

from . import routes  # noqa: E402,F401 - ensure routes get registered

__all__ = ["bp"]

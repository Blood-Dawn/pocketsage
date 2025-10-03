"""Liabilities blueprint package."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "liabilities",
    __name__,
    url_prefix="/liabilities",
    template_folder="../../templates/liabilities",
)

from . import routes  # noqa: E402,F401

__all__ = ["bp"]

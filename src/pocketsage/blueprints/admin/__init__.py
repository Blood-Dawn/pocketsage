"""Admin blueprint package."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
    template_folder="../../templates/admin",
)

from . import routes  # noqa: E402,F401

__all__ = ["bp"]

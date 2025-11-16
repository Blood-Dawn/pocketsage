"""Habits blueprint package."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "habits",
    __name__,
    url_prefix="/habits",
    template_folder="../../templates/habits",
)

from . import routes  # noqa: E402,F401 - import routes for registration

__all__ = ["bp"]

"""Home blueprint package."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "home",
    __name__,
    template_folder="../../templates/home",
)

from . import routes  # noqa: E402,F401 - ensure routes register

__all__ = ["bp"]

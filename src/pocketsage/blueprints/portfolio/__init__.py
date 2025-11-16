"""Portfolio blueprint package."""

from __future__ import annotations

from flask import Blueprint

bp = Blueprint(
    "portfolio",
    __name__,
    url_prefix="/portfolio",
    template_folder="../../templates/portfolio",
)

from . import routes  # noqa: E402,F401

__all__ = ["bp"]

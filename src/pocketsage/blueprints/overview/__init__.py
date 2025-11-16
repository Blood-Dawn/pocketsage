"""Overview blueprint package."""

from __future__ import annotations

from flask import Blueprint, Flask

bp = Blueprint(
    "overview",
    __name__,
    url_prefix="/overview",
    template_folder="../../templates/overview",
)


def init_app(app: Flask) -> None:
    """Attach overview helpers to the Flask application."""

    from .services import load_overview_summary

    state = app.extensions.setdefault("overview", {})
    state["summary_loader"] = load_overview_summary


from . import routes  # noqa: E402,F401 - ensure routes register

__all__ = ["bp", "init_app"]

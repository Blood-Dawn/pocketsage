"""Overview dashboard routes."""

from __future__ import annotations

from flask import current_app, render_template

from . import bp
from .services import load_overview_summary


def _resolve_summary_loader():
    state = current_app.extensions.get("overview", {})
    loader = state.get("summary_loader")
    if callable(loader):
        return loader
    return load_overview_summary


@bp.get("/")
def dashboard():
    """Render the portfolio and wellness overview."""

    summary_loader = _resolve_summary_loader()
    summary = summary_loader()

    return render_template("overview/index.html", summary=summary)

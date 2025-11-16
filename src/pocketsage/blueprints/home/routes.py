"""Home routes."""

from __future__ import annotations

from flask import render_template

from . import bp


@bp.get("/")
def landing_page():
    """Render the PocketSage landing page."""

    return render_template("home/index.html")

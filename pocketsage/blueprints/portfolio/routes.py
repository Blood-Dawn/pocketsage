"""Portfolio routes."""

from __future__ import annotations

from flask import flash, redirect, render_template, url_for

from . import bp


@bp.get("/")
def list_portfolio():
    """Show current holdings and allocation summary."""

    # TODO(@portfolio-squad): fetch holdings + allocation data for template.
    return render_template("portfolio/index.html")


@bp.post("/import")
def import_portfolio():
    """Handle CSV upload for portfolio positions."""

    # TODO(@portfolio-squad): invoke CSV importer with uploaded file.
    flash("Portfolio import not yet implemented", "warning")
    return redirect(url_for("portfolio.list_portfolio"))


@bp.get("/upload")
def upload_portfolio():
    """Render upload form for portfolio CSV."""

    # TODO(@portfolio-squad): wire file upload form + validation messaging.
    return render_template("portfolio/upload.html")

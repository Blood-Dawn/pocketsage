"""Portfolio routes."""

from __future__ import annotations

from pathlib import Path

from flask import current_app, flash, redirect, render_template, request, url_for

from ...services.import_csv import ColumnMapping, import_csv_file
from . import bp


@bp.get("/")
def list_portfolio():
    """Show current holdings and allocation summary."""

    # TODO(@portfolio-squad): fetch holdings + allocation data for template.
    return render_template("portfolio/index.html")


@bp.post("/import")
def import_portfolio():
    """Handle CSV upload for portfolio positions."""
    f = request.files.get("file")
    if not f:
        flash("No file uploaded", "warning")
        return redirect(url_for("portfolio.list_portfolio"))

    upload_dir = Path(current_app.instance_path) / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    filename = f.filename or "uploaded_file.csv"
    file_path = upload_dir / filename
    f.save(str(file_path))

    mapping = ColumnMapping(
        amount="amount", occurred_at="date", memo="memo", external_id="external_id"
    )
    try:
        count = import_csv_file(csv_path=file_path, mapping=mapping)
        flash(f"Imported {count} portfolio rows (preview) - persistence not yet wired", "success")
    except Exception:
        flash("Failed to import CSV", "danger")

    return redirect(url_for("portfolio.list_portfolio"))


@bp.get("/upload")
def upload_portfolio():
    """Render upload form for portfolio CSV."""

    # TODO(@portfolio-squad): wire file upload form + validation messaging.
    return render_template("portfolio/upload.html")

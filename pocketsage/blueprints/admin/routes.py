"""Admin routes for PocketSage."""

from __future__ import annotations

from flask import flash, redirect, render_template, url_for

from . import bp
from .tasks import run_demo_seed, run_export


@bp.get("/")
def dashboard():
    """Display admin dashboard actions."""

    # TODO(@admin-squad): expose system status, last import timestamps, etc.
    return render_template("admin/index.html")


@bp.post("/seed-demo")
def seed_demo():
    """Seed demo data into the database."""

    # TODO(@admin-squad): add confirmation + background task handling.
    run_demo_seed()
    flash("Demo data seeding scheduled", "success")
    return redirect(url_for("admin.dashboard"))


@bp.post("/export")
def export_reports():
    """Trigger report export archive creation."""

    # TODO(@admin-squad): stream export file or email to user.
    run_export()
    flash("Report export scheduled", "info")
    return redirect(url_for("admin.dashboard"))

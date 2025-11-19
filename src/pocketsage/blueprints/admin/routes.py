"""Admin routes for PocketSage."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from flask import (
    current_app,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from sqlmodel import select

from pocketsage.extensions import session_scope
from pocketsage.models import Transaction
from pocketsage.services.jobs import enqueue, get_job, list_jobs

from . import bp
from .tasks import run_demo_seed, run_export


def _prefers_json_response() -> bool:
    accepts = request.accept_mimetypes
    return request.is_json or accepts["application/json"] >= accepts["text/html"]


def _resolve_exports_dir() -> Path:
    configured = current_app.config.get("POCKETSAGE_EXPORTS_DIR")
    if configured:
        return Path(configured)
    return Path(current_app.instance_path) / "exports"


def _recent_exports_metadata(exports_dir: Path, *, limit: int = 5) -> list[dict]:
    if not exports_dir.exists():
        return []

    archives = sorted(
        exports_dir.glob("pocketsage_export_*.zip"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )
    exports: list[dict] = []
    for archive in archives[:limit]:
        stat = archive.stat()
        exports.append(
            {
                "name": archive.name,
                "path": str(archive),
                "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                "size": stat.st_size,
                "download_url": url_for("admin.export_download", filename=archive.name),
            }
        )

    return exports


@bp.get("/")
def dashboard():
    """Display admin dashboard actions."""
    # Show lightweight system status: counts and last transaction time.
    tx_count: int = 0
    last_tx: Optional[Transaction] = None
    with session_scope() as session:
        txs = session.exec(select(Transaction)).all()
        # Sort in-Python to avoid type-checker issues with column expressions
        txs_sorted = sorted(txs, key=lambda t: t.occurred_at)
        tx_count = len(txs_sorted)
        last_tx = txs_sorted[-1] if txs_sorted else None

    last_tx_time = last_tx.occurred_at.isoformat() if last_tx is not None else None

    exports_dir = _resolve_exports_dir()
    recent_exports = _recent_exports_metadata(exports_dir)
    latest_export = recent_exports[0] if recent_exports else None

    return render_template(
        "admin/index.html",
        stats={"transactions": tx_count, "last_transaction": last_tx_time},
        latest_export=latest_export,
        exports=recent_exports,
        jobs=list_jobs(limit=10),
        exports_available=latest_export is not None,
    )


@bp.post("/seed-demo")
def seed_demo():
    """Seed demo data into the database."""
    # Require an explicit confirmation form value to avoid accidental seeding.
    confirm = request.form.get("confirm")
    if request.is_json:
        payload = request.get_json(silent=True) or {}
        confirm = "1" if payload.get("confirm") else None

    if confirm != "1":
        if _prefers_json_response():
            return jsonify({"error": "confirmation_required"}), 400
        flash("Please confirm demo seeding before proceeding.", "warning")
        return redirect(url_for("admin.dashboard"))

    job = enqueue("seed-demo", run_demo_seed)
    if _prefers_json_response():
        return jsonify(job.to_dict()), 202

    flash(
        "Demo data seeding scheduled: habits include Morning Walk (11/14), "
        "Evening Journal (7/14), and Sunday Meal Prep (1/2) streak snapshots; "
        "liabilities cover Redwood Rewards Card ($5,200 @ 19.99% APR), State "
        "University Loan ($18,250 @ 5.45%), and Canyon Auto Loan ($11,400 @ 6.9%).",
        "success",
    )
    return redirect(url_for("admin.dashboard"))


@bp.post("/export")
def export_reports():
    """Trigger report export archive creation."""
    # Run export in background and write output to the instance exports folder so
    # users can download it from the admin UI once ready.
    exports_dir = _resolve_exports_dir()
    exports_dir.mkdir(parents=True, exist_ok=True)

    job = enqueue(
        "export-reports",
        run_export,
        metadata={"output_dir": str(exports_dir)},
        output_dir=exports_dir,
    )
    if _prefers_json_response():
        return jsonify(job.to_dict()), 202

    flash("Report export scheduled; check the export download link once ready.", "info")
    return redirect(url_for("admin.dashboard"))


@bp.get("/export/download")
def export_download():
    """Download an export ZIP from the instance exports folder."""
    exports_dir = _resolve_exports_dir()
    if not exports_dir.exists():
        flash("No exports available", "warning")
        return redirect(url_for("admin.dashboard"))

    # find most recent pocketsage_export_*.zip file
    zips = sorted(
        exports_dir.glob("pocketsage_export_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True
    )
    if not zips:
        flash("No exports available", "warning")
        return redirect(url_for("admin.dashboard"))

    requested_name = request.args.get("filename")
    selected_path = zips[0]
    if requested_name:
        exports_root = exports_dir.resolve()
        candidate = (exports_dir / requested_name).resolve(strict=False)
        if (
            candidate.exists()
            and candidate.is_file()
            and candidate.suffix == ".zip"
            and candidate.parent == exports_root
            and candidate.name.startswith("pocketsage_export_")
        ):
            selected_path = candidate
        else:
            flash("Requested export not found", "warning")
            return redirect(url_for("admin.dashboard"))

    return send_file(selected_path, as_attachment=True)


@bp.get("/jobs/<job_id>")
def job_status(job_id: str):
    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "job_not_found", "job_id": job_id}), 404
    return jsonify(job)

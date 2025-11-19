"""Liability routes."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Iterable, List

from flask import flash, jsonify, redirect, render_template, request, url_for

from pocketsage.services.jobs import enqueue, get_job, list_jobs

from . import bp
from .forms import DEFAULT_STRATEGIES, LiabilityForm


def _currency(amount: float | None) -> str:
    return f"${(amount or 0.0):,.2f}"


def _percentage(amount: float | None) -> str:
    return f"{(amount or 0.0):.2f}%"


def _prefers_json_response() -> bool:
    accepts = request.accept_mimetypes
    return request.is_json or accepts["application/json"] >= accepts["text/html"]


def _sample_liabilities() -> List[dict]:
    """Temporary stub data until repository integration lands."""

    now = datetime.now(timezone.utc)
    return [
        {
            "id": 1,
            "name": "Student Loan Consolidation",
            "balance": 28456.72,
            "apr": 4.65,
            "minimum_payment": 320.0,
            "strategy": "snowball",
            "next_due_display": (now + timedelta(days=9)).strftime("%b %d"),
            "last_recalculated_at": (now - timedelta(days=3)).isoformat(),
            "last_recalculated_display": (now - timedelta(days=3)).strftime("%b %d, %Y"),
        },
        {
            "id": 2,
            "name": "Credit Card Payoff",
            "balance": 5123.09,
            "apr": 17.99,
            "minimum_payment": 150.0,
            "strategy": "avalanche",
            "next_due_display": (now + timedelta(days=5)).strftime("%b %d"),
            "last_recalculated_at": (now - timedelta(days=11)).isoformat(),
            "last_recalculated_display": (now - timedelta(days=11)).strftime("%b %d, %Y"),
        },
        {
            "id": 3,
            "name": "Auto Loan",
            "balance": 17980.41,
            "apr": 3.25,
            "minimum_payment": 410.0,
            "strategy": "snowball",
            "next_due_display": (now + timedelta(days=12)).strftime("%b %d"),
            "last_recalculated_at": (now - timedelta(days=1)).isoformat(),
            "last_recalculated_display": (now - timedelta(days=1)).strftime("%b %d, %Y"),
        },
    ]


def _liability_jobs(liabilities: Iterable[dict]) -> list[dict]:
    liability_ids = {liability["id"] for liability in liabilities}
    relevant: list[dict] = []
    for job in list_jobs(limit=50):
        metadata = job.get("metadata") or {}
        liability_id = metadata.get("liability_id")
        try:
            as_int = int(liability_id)
        except (TypeError, ValueError):
            continue
        if as_int in liability_ids:
            relevant.append(job)
    return relevant


@bp.get("/")
def list_liabilities():
    """Display liabilities overview with payoff projections."""

    # TODO(@debts-squad): hydrate context with repository data + payoff analytics.
    liabilities = _sample_liabilities()
    jobs = _liability_jobs(liabilities)
    return render_template(
        "liabilities/index.html",
        liabilities=liabilities,
        initial_jobs=jobs,
        job_status_endpoint=url_for("liabilities.job_status", job_id="__JOB__"),
    )


def _run_recalculation(liability_id: int) -> None:
    """Placeholder recalculation task."""

    # TODO(@debts-squad): call debts service to recompute schedule and persist results.
    return None


@bp.post("/<int:liability_id>/recalculate")
def recalc_liability(liability_id: int):
    """Trigger payoff schedule recalculation for a liability."""

    job = enqueue(
        "liability-recalculation",
        _run_recalculation,
        metadata={"liability_id": liability_id},
        liability_id=liability_id,
    )
    if _prefers_json_response():
        return jsonify(job.to_dict()), 202

    flash(f"Recalculation queued for liability #{liability_id}", "info")
    return redirect(url_for("liabilities.list_liabilities"))


@bp.get("/jobs/<job_id>")
def job_status(job_id: str):
    """Expose job status for liability recalculations."""

    job = get_job(job_id)
    if job is None:
        return jsonify({"error": "job_not_found", "job_id": job_id}), 404
    return jsonify(job)


@bp.get("/new")
def new_liability():
    """Render creation form for a liability."""

    form = LiabilityForm(
        name="Capital One Venture",
        balance=Decimal("6240.18"),
        apr=Decimal("23.99"),
        minimum_payment=Decimal("160.00"),
        target_strategy="avalanche",
    )
    return render_template(
        "liabilities/form.html",
        form=form,
        strategy_choices=DEFAULT_STRATEGIES,
    )


@bp.post("/new")
def create_liability():
    """Validate liability payload and queue persistence."""

    form = LiabilityForm(
        name=request.form.get("name", ""),
        balance=request.form.get("balance"),
        apr=request.form.get("apr"),
        minimum_payment=request.form.get("minimum_payment"),
        target_strategy=request.form.get("target_strategy", ""),
    )

    if form.validate(strategies=DEFAULT_STRATEGIES):
        # TODO(@debts-squad): persist liability using repository and kickoff payoff plan.
        flash("Liability saved! We'll crunch the payoff plan next.", "success")
        return redirect(url_for("liabilities.list_liabilities"))

    return (
        render_template(
            "liabilities/form.html",
            form=form,
            strategy_choices=DEFAULT_STRATEGIES,
        ),
        400,
    )

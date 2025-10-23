"""Liability routes."""

from __future__ import annotations

from decimal import Decimal

from flask import flash, redirect, render_template, request, url_for

from . import bp
from .forms import DEFAULT_STRATEGIES, LiabilityForm


@bp.get("/")
def list_liabilities():
    """Display liabilities overview with payoff projections."""

    # TODO(@debts-squad): hydrate context with repository data + payoff analytics.
    return render_template("liabilities/index.html")


@bp.post("/<int:liability_id>/recalculate")
def recalc_liability(liability_id: int):
    """Trigger payoff schedule recalculation for a liability."""

    # TODO(@debts-squad): call debts service to recompute schedule and persist results.
    flash(f"Recalculation queued for liability #{liability_id}", "info")
    return redirect(url_for("liabilities.list_liabilities"))


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

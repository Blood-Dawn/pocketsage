"""Liability routes."""

from __future__ import annotations

from flask import flash, redirect, render_template, url_for

from ...services import liabilities as liabilities_service

from . import bp


@bp.get("/")
def list_liabilities():
    """Display liabilities overview with payoff projections."""

    overview = liabilities_service.compute_overview()
    return render_template("liabilities/index.html", overview=overview)


@bp.post("/<int:liability_id>/recalculate")
def recalc_liability(liability_id: int):
    """Trigger payoff schedule recalculation for a liability."""

    # TODO(@debts-squad): call debts service to recompute schedule and persist results.
    flash(f"Recalculation queued for liability #{liability_id}", "info")
    return redirect(url_for("liabilities.list_liabilities"))


@bp.get("/new")
def new_liability():
    """Render creation form for a liability."""

    # TODO(@debts-squad): supply LiabilityForm defaults via forms module.
    return render_template("liabilities/form.html")

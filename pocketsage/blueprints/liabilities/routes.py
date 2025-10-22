"""Liability routes."""

from __future__ import annotations

from datetime import date
from typing import Any

from flask import flash, redirect, render_template, url_for

from ...extensions import session_scope
from . import bp
from .repository import SqlModelLiabilitiesRepository


def _currency(amount: float | None) -> str:
    return f"${(amount or 0.0):,.2f}"


def _percentage(amount: float | None) -> str:
    return f"{(amount or 0.0):.2f}%"


@bp.get("/")
def list_liabilities():
    """Display liabilities overview with payoff projections."""

    today = date.today()
    with session_scope() as session:
        repo = SqlModelLiabilitiesRepository(session)
        liabilities = list(repo.list_liabilities())
        schedule_map = repo.build_schedules(liabilities=liabilities)

    liability_views: list[dict[str, Any]] = []
    upcoming_rows: list[dict[str, Any]] = []
    total_balance = 0.0
    total_minimum = 0.0

    for liability in liabilities:
        liability_id = liability.id
        schedule = schedule_map.get(liability_id, []) if liability_id is not None else []
        total_balance += float(liability.balance or 0.0)
        total_minimum += float(liability.minimum_payment or 0.0)

        total_paid = sum(row.payment for row in schedule)
        total_interest = sum(row.interest for row in schedule)
        next_payment = schedule[0] if schedule else None
        months_to_payoff = len(schedule)

        view_schedule: list[dict[str, Any]] = []
        for index, row in enumerate(schedule):
            days_until = (row.due_date - today).days
            view_schedule.append(
                {
                    "due_date": row.due_date,
                    "due_display": row.due_date.strftime("%b %d, %Y"),
                    "payment": row.payment,
                    "payment_display": _currency(row.payment),
                    "principal": row.principal,
                    "principal_display": _currency(row.principal),
                    "interest": row.interest,
                    "interest_display": _currency(row.interest),
                    "remaining_balance": row.remaining_balance,
                    "remaining_display": _currency(row.remaining_balance),
                    "days_until": days_until,
                }
            )
            if liability_id is not None and index < 12:
                upcoming_rows.append(
                    {
                        "liability_id": liability_id,
                        "liability_name": liability.name,
                        "strategy": liability.payoff_strategy,
                        "due_date": row.due_date,
                        "due_iso": row.due_date.isoformat(),
                        "due_display": row.due_date.strftime("%b %d, %Y"),
                        "payment_display": _currency(row.payment),
                        "days_until": days_until,
                    }
                )

        liability_views.append(
            {
                "id": liability_id,
                "name": liability.name,
                "balance": float(liability.balance or 0.0),
                "balance_display": _currency(liability.balance),
                "apr": float(liability.apr or 0.0),
                "apr_display": _percentage(liability.apr),
                "minimum_payment": float(liability.minimum_payment or 0.0),
                "minimum_payment_display": _currency(liability.minimum_payment),
                "due_day": liability.due_day,
                "payoff_strategy": liability.payoff_strategy,
                "next_payment": (
                    {
                        "due_display": next_payment.due_date.strftime("%b %d, %Y"),
                        "payment_display": _currency(next_payment.payment),
                        "remaining_display": _currency(next_payment.remaining_balance),
                        "due_iso": next_payment.due_date.isoformat(),
                    }
                    if next_payment
                    else None
                ),
                "schedule": view_schedule,
                "total_payment_display": _currency(total_paid),
                "total_interest_display": _currency(total_interest),
                "months_to_payoff": months_to_payoff,
            }
        )

    upcoming_rows.sort(key=lambda row: row["due_date"])

    strategies = sorted(
        {view["payoff_strategy"] for view in liability_views if view["payoff_strategy"]}
    )

    return render_template(
        "liabilities/index.html",
        liabilities=liability_views,
        upcoming_payments=upcoming_rows,
        strategies=strategies,
        totals={
            "balance": _currency(total_balance),
            "minimum": _currency(total_minimum),
            "count": len(liability_views),
        },
        today_label=today.strftime("%b %d, %Y"),
    )


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

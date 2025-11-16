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

    # Call debts service to recompute schedule and persist results.
    repo = get_liability_repository()
    liability = repo.get_by_id(liability_id)
    if not liability:
        flash(f"Liability #{liability_id} not found.", "error")
        return redirect(url_for("liabilities.list_liabilities"))
    
    # Assuming a fixed surplus for this example. This would normally come from user input.
    surplus = 100.0
    
    debt_account = [
        DebtAccount(
            id=liability.id,
            balance=liability.balance,
            apr=liability.apr,
            minimum_payment=liability.minimum_payment,
            statement_due_day=liability.statement_due_day
        )
    ]
    
    # A simple AmortizationWriter to update the repository
    class RepositoryAmortizationWriter:
        def __init__(self, repository):
            self.repository = repository
        
        def write_schedule(self, *, debt_id: int, rows: list[dict]) -> None:
            payoff_schedule = PayoffSchedule(
                schedule_data=rows,
                # Payoff dates are not calculated in this basic implementation,
                # but this is where they would be populated.
                payoff_dates={debt_id: None}
            )
            self.repository.save_payoff_schedule(liability_id=debt_id, schedule=payoff_schedule)
    
    persist_projection(
        writer=RepositoryAmortizationWriter(repo),
        debts=debt_account,
        strategy="avalanche", # Using a default strategy for this example
        surplus=surplus
    )
    
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

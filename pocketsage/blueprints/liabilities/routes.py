"""Liability routes."""

from __future__ import annotations

from calendar import monthrange
from dataclasses import dataclass
from datetime import date
from math import ceil
from typing import Iterable

from flask import flash, redirect, render_template, url_for
from sqlmodel import select

from ...extensions import session_scope
from ...models.liability import Liability
from . import bp


@dataclass(slots=True)
class LiabilityView:
    """Presentation layer model for liabilities."""

    id: int
    name: str
    balance: float
    balance_display: str
    apr_display: str
    minimum_payment_display: str
    strategy: str
    strategy_display: str
    next_due_date: date
    next_due_display: str
    is_overdue: bool
    target_payoff_date: date | None
    target_payoff_display: str
    progress_pct: float
    progress_display: str


def _add_months(start: date, months: int) -> date:
    month = start.month - 1 + months
    year = start.year + month // 12
    month = month % 12 + 1
    day = min(start.day, monthrange(year, month)[1])
    return date(year, month, day)


def _estimate_payoff_date(balance: float, minimum_payment: float, *, base: date) -> date | None:
    if minimum_payment <= 0:
        return None
    months = max(1, ceil(balance / minimum_payment))
    return _add_months(base, months)


def _progress_percentage(*, opened_on: date | None, target: date | None, today: date) -> float:
    if opened_on is None or target is None:
        return 0.0
    total_days = (target - opened_on).days
    if total_days <= 0:
        return 100.0
    elapsed_days = max(0, (today - opened_on).days)
    progress = min(1.0, elapsed_days / total_days)
    return round(progress * 100, 1)


def _normalize_strategy(value: str | None) -> str:
    if not value:
        return "unspecified"
    return value.strip().lower()


def _hydrate_liabilities(liabilities: Iterable[Liability], *, today: date) -> tuple[list[LiabilityView], dict]:
    rows: list[LiabilityView] = []
    total_balance = 0.0
    total_minimum_payment = 0.0
    total_apr = 0.0
    strategy_summary: dict[str, dict[str, float | int]] = {}
    overdue_count = 0

    for liability in liabilities:
        balance = float(liability.balance or 0.0)
        apr = float(liability.apr or 0.0)
        minimum_payment = float(liability.minimum_payment or 0.0)
        strategy = _normalize_strategy(liability.payoff_strategy)

        current_month_due = date(today.year, today.month, liability.due_day)
        is_overdue = current_month_due < today
        if is_overdue:
            overdue_count += 1
            next_due = _add_months(current_month_due, 1)
        else:
            next_due = current_month_due

        target_payoff = _estimate_payoff_date(balance, minimum_payment, base=today)
        progress_pct = _progress_percentage(
            opened_on=liability.opened_on,
            target=target_payoff,
            today=today,
        )

        rows.append(
            LiabilityView(
                id=liability.id or 0,
                name=liability.name,
                balance=balance,
                balance_display=f"${balance:,.2f}",
                apr_display=f"{apr:.2f}%",
                minimum_payment_display=f"${minimum_payment:,.2f}",
                strategy=strategy,
                strategy_display=strategy.replace("_", " ").title(),
                next_due_date=next_due,
                next_due_display=next_due.strftime("%b %d, %Y"),
                is_overdue=is_overdue,
                target_payoff_date=target_payoff,
                target_payoff_display=target_payoff.strftime("%b %d, %Y") if target_payoff else "—",
                progress_pct=progress_pct,
                progress_display=f"{progress_pct:.0f}%",
            )
        )

        total_balance += balance
        total_minimum_payment += minimum_payment
        total_apr += apr

        summary = strategy_summary.setdefault(
            strategy,
            {"count": 0, "balance": 0.0, "minimum_payment": 0.0},
        )
        summary["count"] = int(summary["count"]) + 1
        summary["balance"] = float(summary["balance"]) + balance
        summary["minimum_payment"] = float(summary["minimum_payment"]) + minimum_payment

    average_apr = (total_apr / len(rows)) if rows else 0.0
    summary_payload = {
        "total_balance": total_balance,
        "total_balance_display": f"${total_balance:,.2f}",
        "total_minimum_payment": total_minimum_payment,
        "total_minimum_payment_display": f"${total_minimum_payment:,.2f}",
        "average_apr": average_apr,
        "average_apr_display": f"{average_apr:.2f}%",
        "overdue_count": overdue_count,
        "strategies": [
            {
                "name": name,
                "label": name.replace("_", " ").title(),
                "count": data["count"],
                "balance": data["balance"],
                "balance_display": f"${float(data['balance']):,.2f}",
                "minimum_payment": data["minimum_payment"],
                "minimum_payment_display": f"${float(data['minimum_payment']):,.2f}",
            }
            for name, data in sorted(strategy_summary.items())
        ],
    }

    rows.sort(key=lambda entry: entry.balance, reverse=True)
    return rows, summary_payload


@bp.get("/")
def list_liabilities():
    """Display liabilities overview with payoff projections."""

    today = date.today()
    with session_scope() as session:
        liabilities = session.exec(select(Liability)).all()

    liability_rows, summary = _hydrate_liabilities(liabilities, today=today)

    return render_template(
        "liabilities/index.html",
        liabilities=liability_rows,
        summary=summary,
        today=today,
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

"""Liability routes."""

from __future__ import annotations

from decimal import Decimal

from flask import flash, redirect, render_template, request, url_for

from . import bp
from .forms import DEFAULT_STRATEGIES, LiabilityForm

from pocketsage.blueprints.liabilities import bp
from pocketsage.repository import get_liability_repository
from pocketsage.services.debts import DebtAccount, persist_projection
from pocketsage.forms.liability_forms import LiabilityForm
from pocketsage.repository import Liability, PayoffSchedule
from pocketsage.services.debts import persist_projection, get_debt_accounts
from pocketsage.services.reports import generate_payoff_timeline

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

    overview = liabilities_service.compute_overview()
    return render_template("liabilities/index.html", overview=overview)


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

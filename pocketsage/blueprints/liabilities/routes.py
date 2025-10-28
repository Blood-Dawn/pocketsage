"""Liability routes."""

from __future__ import annotations

from flask import flash, redirect, render_template, url_for, g

from pocketsage.blueprints.liabilities import bp
from pocketsage.repository import get_liability_repository
from pocketsage.services.debts import DebtAccount, persist_projection
from pocketsage.forms.liability_forms import LiabilityForm
from pocketsage.repository import Liability, PayoffSchedule
from pocketsage.services.debts import persist_projection, get_debt_accounts
from pocketsage.services.reports import generate_payoff_timeline

@bp.get("/")
def list_liabilities():
    """Display liabilities overview with payoff projections."""

    # Hydrate context with repository data + payoff analytics.
    repo = get_liability_repository()
    user_id = g.user.id if hasattr(g, 'user') else 1 # Placeholder for authenticated user ID
    liabilities = repo.get_all(user_id=user_id)
    
    context = {
        'liabilities': liabilities,
    }
    
    return render_template("liabilities/index.html", **context)


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

    # Supply LiabilityForm defaults via forms module.
    form = LiabilityForm()
    return render_template("liabilities/form.html", form=form)

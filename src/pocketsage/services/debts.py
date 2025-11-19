"""Debt payoff calculators."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Iterable, Protocol


@dataclass(slots=True)
class DebtAccount:
    """Represents a liability input for payoff projections."""

    id: int
    balance: float
    apr: float
    minimum_payment: float
    statement_due_day: int  # Day of the month the statement is due
    extra_payment: float = 0.0  # Additional payment amount, with a default of 0.0


class AmortizationWriter(Protocol):
    """Persists payoff projections for later retrieval."""

    def write_schedule(
        self, *, debt_id: int, rows: list[dict]
    ) -> None:  # pragma: no cover - interface
        ...


def _calculate_schedule(*, debts: Iterable[DebtAccount], surplus: float) -> list[dict]:
    """Helper function to perform the amortization math."""
    debts = [d.__dict__ for d in debts]  # Convert to mutable dicts
    payoff_schedule = []
    current_date = date.today().replace(day=1)

    while any(d["balance"] > 0 for d in debts):
        extra_payment_pool = surplus

        # Add freed-up minimum payments from paid-off debts to the extra payment pool
        if payoff_schedule:
            last_row = payoff_schedule[-1]
            extra_payment_pool += sum(
                last_row.get(f'min_payment_{d["id"]}', 0) for d in debts if d["balance"] == 0
            )

        # Create a new row for the current month
        row = {"date": current_date.isoformat(), "payments": {}}

        # Apply payments to each debt
        for i, debt in enumerate(debts):
            if debt["balance"] > 0:
                monthly_interest = Decimal(debt["balance"]) * Decimal(debt["apr"]) / Decimal(1200)
                monthly_interest_float = float(
                    monthly_interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                )

                # Payment logic (target is the first debt in the sorted list)
                if i == 0:
                    payment = debt["minimum_payment"] + extra_payment_pool
                else:
                    payment = debt["minimum_payment"]

                # Apply payment, ensuring the balance does not go below zero
                new_balance = debt["balance"] + monthly_interest_float - payment

                if new_balance <= 0:
                    payment_to_apply = debt["balance"] + monthly_interest_float
                    debt["balance"] = 0
                    extra_payment_pool = payment - payment_to_apply  # Carry over extra payment
                else:
                    debt["balance"] = new_balance

                row["payments"][f'debt_{debt["id"]}'] = {
                    "payment_amount": payment,
                    "interest_paid": monthly_interest_float,
                    "remaining_balance": debt["balance"],
                }

        payoff_schedule.append(row)
        current_date += timedelta(days=30)  # Approximate month duration
    return payoff_schedule


def snowball_schedule(*, debts: Iterable[DebtAccount], surplus: float) -> list[dict]:
    """Return payoff schedule prioritizing smallest balances first."""
    # Sort debts by balance, ascending.
    sorted_debts = sorted(debts, key=lambda d: d.balance)
    return _calculate_schedule(debts=sorted_debts, surplus=surplus)


def avalanche_schedule(*, debts: Iterable[DebtAccount], surplus: float) -> list[dict]:
    """Return payoff schedule prioritizing highest APR first."""
    # Sort debts by APR, descending.
    sorted_debts = sorted(debts, key=lambda d: d.apr, reverse=True)
    return _calculate_schedule(debts=sorted_debts, surplus=surplus)


def persist_projection(
    *, writer: AmortizationWriter, debts: Iterable[DebtAccount], strategy: str, surplus: float
) -> None:
    """Compute schedule for desired strategy and hand to persistence layer."""
    if strategy == "snowball":
        schedule = snowball_schedule(debts=debts, surplus=surplus)
    elif strategy == "avalanche":
        schedule = avalanche_schedule(debts=debts, surplus=surplus)
    else:
        raise ValueError("Invalid debt payoff strategy.")

    for debt in debts:
        writer.write_schedule(debt_id=debt.id, rows=schedule)

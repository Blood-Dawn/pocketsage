"""Debt payoff calculators."""

# TODO(@codex): Debt payoff calculation logic (snowball and avalanche)
#    - Snowball: order debts by ascending balance (DONE)
#    - Avalanche: order by descending APR (DONE)
#    - Simulate month-by-month payments (DONE)
#    - Apply extra payments to target debt after minimums (DONE)
#    - Return payoff schedule with time and total interest (DONE)
#    - Handle edge cases: tiny payments, infinite loops (DONE - progress guard)
#    - Ensure minimum payment always reduces principal (DONE - minimum_progress)

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Iterable, Protocol


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
    debt_dicts: list[dict[str, Any]] = [asdict(d) for d in debts]  # Convert to mutable dicts
    payoff_schedule: list[dict] = []
    current_date = date.today().replace(day=1)
    rolled_minimums = 0.0  # freed minimum payments from debts already cleared
    total_interest = 0.0

    def _next_month(value: date) -> date:
        month = value.month + 1
        year = value.year + (month - 1) // 12
        month = ((month - 1) % 12) + 1
        return value.replace(year=year, month=month, day=1)

    previous_total_balance = sum(d["balance"] for d in debt_dicts)
    stagnant_periods = 0  # used to detect non-decreasing balances

    while any(d["balance"] > 0 for d in debt_dicts):
        extra_pool = surplus + rolled_minimums
        row = {"date": current_date.isoformat(), "payments": {}}

        for debt in debt_dicts:
            if debt["balance"] <= 0:
                continue

            monthly_interest = Decimal(debt["balance"]) * Decimal(debt["apr"]) / Decimal(1200)
            monthly_interest_float = float(
                monthly_interest.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            )
            total_interest += monthly_interest_float

            # Apply surplus to the first active debt each period
            payment = debt["minimum_payment"]
            if extra_pool > 0:
                payment += extra_pool
                extra_pool = 0.0

            # Ensure payment always reduces principal
            minimum_progress = monthly_interest_float + 1.0
            if payment < minimum_progress:
                payment = minimum_progress

            new_balance = debt["balance"] + monthly_interest_float - payment

            if new_balance <= 0:
                payment_to_apply = debt["balance"] + monthly_interest_float
                leftover = payment - payment_to_apply
                debt["balance"] = 0.0
                extra_pool += max(leftover, 0.0)
                rolled_minimums += debt["minimum_payment"]
            else:
                debt["balance"] = new_balance

            row["payments"][f"debt_{debt['id']}"] = {
                "payment_amount": payment,
                "interest_paid": monthly_interest_float,
                "remaining_balance": debt["balance"],
            }

        payoff_schedule.append(row)

        # Progress guard: ensure balances continue to decrease to avoid infinite loops
        total_balance = sum(d["balance"] for d in debt_dicts if d["balance"] > 0)
        if total_balance >= previous_total_balance - 0.01:
            stagnant_periods += 1
        else:
            stagnant_periods = 0
        if stagnant_periods >= 3:
            raise ValueError("Payoff schedule did not converge; payments too low")
        previous_total_balance = total_balance
        current_date = _next_month(current_date)

    return payoff_schedule


def schedule_summary(schedule: list[dict]) -> tuple[str | None, float, int]:
    """Return (payoff_date_iso, total_interest, months)."""

    if not schedule:
        return None, 0.0, 0
    payoff_date = schedule[-1].get("date")
    total_interest = 0.0
    for entry in schedule:
        payments = entry.get("payments", {}) if isinstance(entry, dict) else {}
        for p in payments.values():
            try:
                total_interest += float(p.get("interest_paid", 0.0) or 0.0)
            except Exception:
                continue
    return str(payoff_date) if payoff_date else None, total_interest, len(schedule)


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

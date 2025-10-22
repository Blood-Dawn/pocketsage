"""Utilities for liability payment schedules."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from ..models.liability import Liability


@dataclass(slots=True)
class PaymentProjection:
    """Represents a single projected payment for a liability."""

    due_date: date
    payment: float
    principal: float
    interest: float
    remaining_balance: float


def _initial_due_date(*, today: date, due_day: int) -> date:
    """Return the first due date on or after *today*."""

    year = today.year
    month = today.month
    if today.day > due_day:
        month += 1
    year += (month - 1) // 12
    month = ((month - 1) % 12) + 1
    # Liability due dates are constrained to 1..28 so every month is valid.
    return date(year, month, due_day)


def _advance_due_date(current: date, due_day: int) -> date:
    """Return the due date for the following month."""

    month = current.month + 1
    year = current.year + (month - 1) // 12
    month = ((month - 1) % 12) + 1
    return date(year, month, due_day)


def _normalize_currency(amount: float) -> float:
    """Round to cents using bankers-friendly half-up rounding."""

    return round(amount + 1e-9, 2)


def generate_payment_schedule(
    *, liability: Liability, months: int = 12, today: date | None = None
) -> list[PaymentProjection]:
    """Generate a simple amortization schedule for a liability.

    This helper intentionally favors determinism and readability over
    mathematical precision. The interest calculation assumes a fixed APR
    applied monthly and ensures that every row reduces the remaining balance.
    """

    if liability.balance is None or liability.balance <= 0:
        return []

    current_date = today or date.today()
    balance = max(float(liability.balance), 0.0)
    monthly_rate = max(float(liability.apr or 0.0), 0.0) / 100.0 / 12.0
    minimum_payment = max(float(liability.minimum_payment or 0.0), 0.0)
    due_day = getattr(liability, "due_day", 1) or 1

    schedule: list[PaymentProjection] = []
    next_due = _initial_due_date(today=current_date, due_day=due_day)

    for _ in range(max(1, months)):
        if balance <= 0:
            break

        interest = _normalize_currency(balance * monthly_rate)
        # Ensure we always reduce the balance even when minimum payment is low.
        suggested_payment = max(minimum_payment, interest + 1.0)
        total_due = _normalize_currency(balance + interest)
        payment = _normalize_currency(min(suggested_payment, total_due))
        principal = _normalize_currency(payment - interest)

        balance = _normalize_currency(balance + interest - payment)
        if balance < 0.01:
            balance = 0.0

        schedule.append(
            PaymentProjection(
                due_date=next_due,
                payment=payment,
                principal=principal,
                interest=interest,
                remaining_balance=balance,
            )
        )

        # Prepare the next due date and break once the balance is cleared.
        next_due = _advance_due_date(next_due, due_day)

    return schedule


def flatten_schedules(
    *, liabilities: Iterable[Liability], months: int = 12, today: date | None = None
) -> dict[int, list[PaymentProjection]]:
    """Return payment schedules keyed by liability id."""

    schedules: dict[int, list[PaymentProjection]] = {}
    for liability in liabilities:
        if liability.id is None:
            continue
        schedules[liability.id] = generate_payment_schedule(
            liability=liability, months=months, today=today
        )
    return schedules


__all__ = ["PaymentProjection", "generate_payment_schedule", "flatten_schedules"]

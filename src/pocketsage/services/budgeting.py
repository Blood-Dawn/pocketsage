"""Budgeting domain services."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Protocol

from ..models.transaction import Transaction


class BudgetRepository(Protocol):
    """Abstraction for fetching budget lines and actuals."""

    def planned_amounts(
        self, *, period: str
    ) -> Iterable[tuple[int, float]]:  # pragma: no cover - interface
        """Return (category_id, planned_amount) pairs for the requested period."""
        ...

    def actual_spend(
        self, *, period: str
    ) -> Iterable[tuple[int, float]]:  # pragma: no cover - interface
        """Return (category_id, actual_amount) pairs for the requested period."""
        ...


@dataclass(slots=True)
class BudgetVariance:
    """Lightweight DTO for reporting variance."""

    category_id: int
    planned: float
    actual: float

    @property
    def delta(self) -> float:
        return self.actual - self.planned


def compute_variances(*, repository: BudgetRepository, period: str) -> list[BudgetVariance]:
    """Compose budget vs actual variances for display."""

    planned_map = {cat_id: amount for cat_id, amount in repository.planned_amounts(period=period)}
    actual_map = {cat_id: amount for cat_id, amount in repository.actual_spend(period=period)}

    # Merge categories from both planned and actual
    all_categories = set(planned_map.keys()) | set(actual_map.keys())

    variances = []
    for cat_id in sorted(all_categories):
        planned = round(planned_map.get(cat_id, 0.0), 2)
        actual = round(actual_map.get(cat_id, 0.0), 2)
        variances.append(BudgetVariance(category_id=cat_id, planned=planned, actual=actual))

    return variances


def rolling_cash_flow(*, transactions: Iterable[Transaction], window_days: int) -> list[float]:
    """Return running cashflow totals by day (cumulative net).

    window_days is currently advisory for future smoothing; all days are included
    in the running total to match reports/dashboard expectations.
    """

    sorted_txns = sorted(transactions, key=lambda t: t.occurred_at)
    if not sorted_txns:
        return []

    daily_balances: dict[str, float] = {}
    for txn in sorted_txns:
        date_key = txn.occurred_at.date().isoformat()
        daily_balances[date_key] = daily_balances.get(date_key, 0.0) + float(txn.amount)

    running_total = 0.0
    rolling_values: list[float] = []
    for date_key in sorted(daily_balances.keys()):
        running_total += daily_balances[date_key]
        rolling_values.append(round(running_total, 2))

    return rolling_values

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
        # TODO(@analytics): unit test positive/negative variance semantics.
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
    """Return rolling balances suitable for charting."""

    # Sort transactions by date for deterministic processing
    sorted_txns = sorted(transactions, key=lambda t: t.occurred_at)

    if not sorted_txns:
        return []


    # Build daily balances
    daily_balances: dict[str, float] = {}
    for txn in sorted_txns:
        date_key = txn.occurred_at.date().isoformat()
        daily_balances[date_key] = daily_balances.get(date_key, 0.0) + float(txn.amount)

    # Generate rolling window sums
    if not daily_balances:
        return []

    sorted_dates = sorted(daily_balances.keys())
    rolling_values = []

    for i, current_date_str in enumerate(sorted_dates):
        # Sum all transactions within the window ending on current_date
        window_sum = 0.0
        for j in range(max(0, i - window_days + 1), i + 1):
            window_sum += daily_balances[sorted_dates[j]]
        rolling_values.append(round(window_sum, 2))

    return rolling_values

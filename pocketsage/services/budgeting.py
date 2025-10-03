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

    # TODO(@teammate): implement merging of planned vs actual data with zero-fill
    #   for missing categories and consistent rounding.
    raise NotImplementedError


def rolling_cash_flow(*, transactions: Iterable[Transaction], window_days: int) -> list[float]:
    """Return rolling balances suitable for charting."""

    # TODO(@teammate): implement windowed sum with deterministic ordering + tz handling.
    raise NotImplementedError

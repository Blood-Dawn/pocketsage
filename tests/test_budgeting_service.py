from __future__ import annotations

from datetime import datetime, timedelta
from typing import Iterable

from pocketsage.models.transaction import Transaction
from pocketsage.services import budgeting


class _FakeBudgetRepo(budgeting.BudgetRepository):
    def __init__(self, planned, actual):
        self._planned = planned
        self._actual = actual

    def planned_amounts(self, *, period: str) -> Iterable[tuple[int, float]]:
        return self._planned

    def actual_spend(self, *, period: str) -> Iterable[tuple[int, float]]:
        return self._actual


def test_compute_variances_merges_planned_and_actual():
    repo = _FakeBudgetRepo(
        planned=[(1, 100.0), (2, 50.0)],
        actual=[(2, 75.0), (3, 20.0)],
    )

    result = budgeting.compute_variances(repository=repo, period="2025-01")

    # Sorted by category_id
    assert [v.category_id for v in result] == [1, 2, 3]
    assert [(v.planned, v.actual, v.delta) for v in result] == [
        (100.0, 0.0, -100.0),
        (50.0, 75.0, 25.0),
        (0.0, 20.0, 20.0),
    ]


def test_rolling_cash_flow_computes_window_totals():
    base = datetime(2025, 1, 1)
    txns = [
        Transaction(occurred_at=base, amount=100.0, memo="", user_id=1),
        Transaction(occurred_at=base + timedelta(days=1), amount=-20.0, memo="", user_id=1),
        Transaction(occurred_at=base + timedelta(days=2), amount=10.0, memo="", user_id=1),
    ]

    window = budgeting.rolling_cash_flow(transactions=txns, window_days=2)

    # Rolling sums per day: day0=100, day1=80, day2=90 (window of last 2 days)
    assert window == [100.0, 80.0, 90.0]


def test_rolling_cash_flow_empty_returns_empty():
    assert budgeting.rolling_cash_flow(transactions=[], window_days=3) == []

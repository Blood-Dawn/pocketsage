"""Budgeting service tests."""

from __future__ import annotations

from datetime import datetime

from pocketsage.models.transaction import Transaction
from pocketsage.services import budgeting


class MockBudgetRepository:
    """Mock repository for testing budget variance calculations."""

    def __init__(self, planned_data: list[tuple[int, float]], actual_data: list[tuple[int, float]]):
        self.planned_data = planned_data
        self.actual_data = actual_data

    def planned_amounts(self, *, period: str) -> list[tuple[int, float]]:
        return self.planned_data

    def actual_spend(self, *, period: str) -> list[tuple[int, float]]:
        return self.actual_data


def test_compute_variances_merges_planned_and_actual():
    """Test that budget variance calculation merges planned and actual amounts correctly."""
    mock_repo = MockBudgetRepository(
        planned_data=[(1, 500.0), (2, 200.0)],  # category 1: $500, category 2: $200
        actual_data=[(1, 450.0), (3, 100.0)]    # category 1: $450, category 3: $100
    )

    variances = budgeting.compute_variances(repository=mock_repo, period="2025-10")

    # Should have 3 categories total (1, 2, 3)
    assert len(variances) == 3

    # Verify category 1: planned $500, actual $450, delta -$50
    var1 = next(v for v in variances if v.category_id == 1)
    assert var1.planned == 500.0
    assert var1.actual == 450.0
    assert var1.delta == -50.0

    # Verify category 2: planned $200, actual $0, delta -$200
    var2 = next(v for v in variances if v.category_id == 2)
    assert var2.planned == 200.0
    assert var2.actual == 0.0
    assert var2.delta == -200.0

    # Verify category 3: planned $0, actual $100, delta $100
    var3 = next(v for v in variances if v.category_id == 3)
    assert var3.planned == 0.0
    assert var3.actual == 100.0
    assert var3.delta == 100.0


def test_rolling_cash_flow_window_balances():
    """Test rolling cash flow calculation with a 7-day window."""
    # Create sample transactions
    transactions = [
        Transaction(id=1, occurred_at=datetime(2025, 1, 1, 12, 0), amount=100.0, description="Day 1", category_id=1),
        Transaction(id=2, occurred_at=datetime(2025, 1, 2, 12, 0), amount=50.0, description="Day 2", category_id=1),
        Transaction(id=3, occurred_at=datetime(2025, 1, 3, 12, 0), amount=-30.0, description="Day 3", category_id=1),
    ]

    result = budgeting.rolling_cash_flow(transactions=transactions, window_days=7)

    # Should have 3 data points (one per date)
    assert len(result) == 3

    # Day 1: sum of day 1 only = 100
    assert result[0] == 100.0

    # Day 2: sum of days 1-2 = 150
    assert result[1] == 150.0

    # Day 3: sum of days 1-3 = 120
    assert result[2] == 120.0
def test_rolling_cash_flow_empty_transactions():
    """Test rolling cash flow with no transactions returns empty list."""
    result = budgeting.rolling_cash_flow(transactions=[], window_days=7)
    assert result == []


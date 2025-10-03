"""Budgeting service tests."""

from __future__ import annotations

import pytest
from pocketsage.services import budgeting


@pytest.mark.skip(reason="TODO(@qa-team): implement budget variance calculation happy-path test.")
def test_compute_variances_merges_planned_and_actual():
    assert budgeting.compute_variances(repository=None, period="2025-10")  # type: ignore[arg-type]


@pytest.mark.skip(reason="TODO(@qa-team): implement rolling cash flow window test.")
def test_rolling_cash_flow_window_balances():
    assert budgeting.rolling_cash_flow(transactions=[], window_days=7) == []

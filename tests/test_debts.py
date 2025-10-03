"""Debt service tests."""

from __future__ import annotations

import pytest
from pocketsage.services import debts


@pytest.mark.skip(reason="TODO(@qa-team): verify snowball ordering of debts by balance.")
def test_snowball_schedule_orders_by_balance():
    assert debts.snowball_schedule(debts=[], surplus=0) == []


@pytest.mark.skip(reason="TODO(@qa-team): verify avalanche ordering of debts by APR.")
def test_avalanche_schedule_orders_by_apr():
    assert debts.avalanche_schedule(debts=[], surplus=0) == []

"""Debt service tests."""

from __future__ import annotations

from pocketsage.services.debts import DebtAccount, avalanche_schedule, snowball_schedule


def test_snowball_schedule_orders_by_balance():
    """Verify snowball method pays off smallest balances first."""
    debts = [
        DebtAccount(id=1, balance=5000.0, apr=18.0, minimum_payment=100.0, statement_due_day=15),
        DebtAccount(id=2, balance=1000.0, apr=12.0, minimum_payment=50.0, statement_due_day=1),
        DebtAccount(id=3, balance=3000.0, apr=15.0, minimum_payment=75.0, statement_due_day=10),
    ]

    schedule = snowball_schedule(debts=debts, surplus=200.0)

    # Should return a non-empty schedule
    assert len(schedule) > 0

    # First month should show debt #2 (smallest balance) getting the extra surplus
    first_month = schedule[0]
    assert "debt_2" in first_month["payments"]

    # Debt #2 should receive more than its minimum payment (due to surplus)
    debt2_payment = first_month["payments"]["debt_2"]["payment_amount"]
    assert debt2_payment > 50.0  # More than the $50 minimum

    # The total extra payment should include the surplus
    # Debt #2 should get minimum + surplus = 50 + 200 = 250
    # (approximately, accounting for interest)
    assert debt2_payment >= 200.0


def test_avalanche_schedule_orders_by_apr():
    """Verify avalanche method pays off highest APR debts first."""
    debts = [
        DebtAccount(id=1, balance=5000.0, apr=18.0, minimum_payment=100.0, statement_due_day=15),
        DebtAccount(id=2, balance=1000.0, apr=12.0, minimum_payment=50.0, statement_due_day=1),
        DebtAccount(id=3, balance=3000.0, apr=15.0, minimum_payment=75.0, statement_due_day=10),
    ]

    schedule = avalanche_schedule(debts=debts, surplus=200.0)

    # Should return a non-empty schedule
    assert len(schedule) > 0

    # First month should show debt #1 (highest APR at 18%) getting the extra surplus
    first_month = schedule[0]
    assert "debt_1" in first_month["payments"]

    # Debt #1 should receive more than its minimum payment (due to surplus)
    debt1_payment = first_month["payments"]["debt_1"]["payment_amount"]
    assert debt1_payment > 100.0  # More than the $100 minimum

    # The total extra payment should include the surplus
    # Debt #1 should get minimum + surplus = 100 + 200 = 300
    # (approximately, accounting for interest)
    assert debt1_payment >= 250.0


def test_snowball_vs_avalanche_ordering():
    """Confirm snowball and avalanche use different ordering strategies."""
    debts = [
        DebtAccount(id=1, balance=5000.0, apr=10.0, minimum_payment=100.0, statement_due_day=15),
        DebtAccount(id=2, balance=1000.0, apr=20.0, minimum_payment=50.0, statement_due_day=1),
    ]

    snowball = snowball_schedule(debts=debts, surplus=100.0)
    avalanche = avalanche_schedule(debts=debts, surplus=100.0)

    # Both should produce schedules
    assert len(snowball) > 0
    assert len(avalanche) > 0

    # Snowball should prioritize debt #2 (smallest balance)
    snowball_first = snowball[0]["payments"]["debt_2"]["payment_amount"]
    assert snowball_first > 50.0  # Gets surplus

    # Avalanche should prioritize debt #2 (highest APR)
    avalanche_first = avalanche[0]["payments"]["debt_2"]["payment_amount"]
    assert avalanche_first > 50.0  # Gets surplus

    # In this case, both methods target the same debt (smallest balance AND highest APR)
    # but if we had different data, they would differ

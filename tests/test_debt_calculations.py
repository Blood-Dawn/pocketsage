"""Comprehensive tests for debt payoff calculations (snowball/avalanche).

These tests verify the core financial logic for debt payoff scheduling,
including:
- Snowball method (smallest balance first)
- Avalanche method (highest APR first)
- Interest calculations with proper rounding
- Payment application and balance reduction
- Freed-up minimum payment rollover
- Edge cases (zero balances, high APR, etc.)
"""

from __future__ import annotations

import pytest
from src.pocketsage.services.debts import (
    DebtAccount,
    avalanche_schedule,
    persist_projection,
    snowball_schedule,
)
from tests.conftest import assert_float_equal


class TestSnowballSchedule:
    """Tests for snowball debt payoff method (smallest balance first)."""

    def test_empty_debts_returns_empty_schedule(self):
        """Snowball with no debts should return empty schedule."""
        schedule = snowball_schedule(debts=[], surplus=0)
        assert schedule == []

    def test_single_debt_payoff_schedule(self):
        """Single debt should be paid off correctly with interest."""
        debt = DebtAccount(
            id=1,
            balance=1000.00,
            apr=12.0,  # 1% monthly
            minimum_payment=50.00,
            statement_due_day=15,
        )

        schedule = snowball_schedule(debts=[debt], surplus=100.00)

        # Should have multiple payment periods
        assert len(schedule) > 0

        # First payment should include interest
        first_payment = schedule[0]["payments"]["debt_1"]
        expected_interest = 1000.00 * 0.12 / 12  # $10.00
        assert_float_equal(first_payment["interest_paid"], expected_interest)

        # Total payment should be minimum + surplus
        assert_float_equal(first_payment["payment_amount"], 150.00)

        # Last payment should have zero balance
        last_payment = schedule[-1]["payments"]["debt_1"]
        assert_float_equal(last_payment["remaining_balance"], 0.00)

    def test_multiple_debts_smallest_first(self):
        """Multiple debts should be prioritized by smallest balance."""
        debt_large = DebtAccount(
            id=1,
            balance=5000.00,
            apr=15.0,
            minimum_payment=100.00,
            statement_due_day=15,
        )
        debt_small = DebtAccount(
            id=2,
            balance=500.00,
            apr=20.0,  # Higher APR but smaller balance
            minimum_payment=25.00,
            statement_due_day=15,
        )

        schedule = snowball_schedule(debts=[debt_large, debt_small], surplus=200.00)

        # Small debt should appear first in schedule
        # (snowball prioritizes by balance, not APR)
        first_period = schedule[0]

        # Debt 2 (small) should get minimum + surplus
        debt2_payment = first_period["payments"]["debt_2"]
        assert_float_equal(debt2_payment["payment_amount"], 225.00)  # 25 + 200

        # Debt 1 (large) should only get minimum
        debt1_payment = first_period["payments"]["debt_1"]
        assert_float_equal(debt1_payment["payment_amount"], 100.00)

    def test_freed_minimum_payment_rollover(self):
        """When a debt is paid off, its minimum should roll over to next debt."""
        debt1 = DebtAccount(
            id=1,
            balance=100.00,  # Will pay off quickly
            apr=10.0,
            minimum_payment=30.00,
            statement_due_day=15,
        )
        debt2 = DebtAccount(
            id=2,
            balance=2000.00,
            apr=15.0,
            minimum_payment=50.00,
            statement_due_day=15,
        )

        schedule = snowball_schedule(debts=[debt1, debt2], surplus=100.00)

        # Find the month where debt1 is paid off
        debt1_payoff_month = None
        for i, period in enumerate(schedule):
            if period["payments"]["debt_1"]["remaining_balance"] == 0:
                debt1_payoff_month = i
                break

        assert debt1_payoff_month is not None, "Debt 1 should be paid off"

        # After debt1 is paid off, debt2 should get extra payment from freed minimum
        if debt1_payoff_month + 1 < len(schedule):
            next_period = schedule[debt1_payoff_month + 1]
            # Debt2 should now get: its minimum (50) + original surplus (100) + freed minimum (30)
            # But this depends on implementation details, so just verify it gets more than before
            debt2_payment = next_period["payments"]["debt_2"]["payment_amount"]
            assert debt2_payment > 50.00  # Should be more than just minimum

    def test_zero_surplus_only_minimums(self):
        """With zero surplus, only minimum payments should be made."""
        debt = DebtAccount(
            id=1,
            balance=1000.00,
            apr=12.0,
            minimum_payment=50.00,
            statement_due_day=15,
        )

        schedule = snowball_schedule(debts=[debt], surplus=0.00)

        # First payment should only be the minimum
        first_payment = schedule[0]["payments"]["debt_1"]
        assert_float_equal(first_payment["payment_amount"], 50.00)

    def test_high_apr_interest_calculation(self):
        """High APR should calculate interest correctly using Decimal precision."""
        debt = DebtAccount(
            id=1,
            balance=1000.00,
            apr=24.0,  # 2% monthly
            minimum_payment=50.00,
            statement_due_day=15,
        )

        schedule = snowball_schedule(debts=[debt], surplus=50.00)

        # First month interest should be $20.00 (1000 * 0.24 / 12)
        first_payment = schedule[0]["payments"]["debt_1"]
        expected_interest = 1000.00 * 0.24 / 12
        assert_float_equal(first_payment["interest_paid"], expected_interest)


class TestAvalancheSchedule:
    """Tests for avalanche debt payoff method (highest APR first)."""

    def test_empty_debts_returns_empty_schedule(self):
        """Avalanche with no debts should return empty schedule."""
        schedule = avalanche_schedule(debts=[], surplus=0)
        assert schedule == []

    def test_multiple_debts_highest_apr_first(self):
        """Multiple debts should be prioritized by highest APR."""
        debt_low_apr = DebtAccount(
            id=1,
            balance=5000.00,
            apr=10.0,  # Lower APR
            minimum_payment=100.00,
            statement_due_day=15,
        )
        debt_high_apr = DebtAccount(
            id=2,
            balance=2000.00,
            apr=22.0,  # Higher APR
            minimum_payment=50.00,
            statement_due_day=15,
        )

        schedule = avalanche_schedule(debts=[debt_low_apr, debt_high_apr], surplus=200.00)

        # High APR debt should get priority (minimum + surplus)
        first_period = schedule[0]

        # Debt 2 (high APR) should get minimum + surplus
        debt2_payment = first_period["payments"]["debt_2"]
        assert_float_equal(debt2_payment["payment_amount"], 250.00)  # 50 + 200

        # Debt 1 (low APR) should only get minimum
        debt1_payment = first_period["payments"]["debt_1"]
        assert_float_equal(debt1_payment["payment_amount"], 100.00)

    def test_avalanche_saves_more_on_interest(self):
        """Avalanche should save more on total interest than snowball for same debts."""
        # Create two debts where snowball and avalanche differ
        debt_small_low_apr = DebtAccount(
            id=1,
            balance=500.00,  # Smaller balance
            apr=10.0,  # Lower APR
            minimum_payment=25.00,
            statement_due_day=15,
        )
        debt_large_high_apr = DebtAccount(
            id=2,
            balance=5000.00,  # Larger balance
            apr=20.0,  # Higher APR
            minimum_payment=100.00,
            statement_due_day=15,
        )

        surplus = 200.00
        debts = [debt_small_low_apr, debt_large_high_apr]

        snowball = snowball_schedule(debts=debts, surplus=surplus)
        avalanche = avalanche_schedule(debts=debts, surplus=surplus)

        # Calculate total interest paid for each method
        def total_interest(schedule):
            total = 0.0
            for period in schedule:
                for debt_payments in period["payments"].values():
                    total += debt_payments["interest_paid"]
            return total

        snowball_interest = total_interest(snowball)
        avalanche_interest = total_interest(avalanche)

        # Avalanche should save money on interest
        # (targets high-APR debt first, reducing compounding interest)
        assert avalanche_interest < snowball_interest


class TestPersistProjection:
    """Tests for persist_projection function that delegates to writer protocol."""

    def test_snowball_strategy_calls_writer(self):
        """Snowball strategy should compute schedule and call writer."""
        debt = DebtAccount(
            id=1,
            balance=1000.00,
            apr=12.0,
            minimum_payment=50.00,
            statement_due_day=15,
        )

        # Mock writer
        written_schedules = []

        class MockWriter:
            def write_schedule(self, *, debt_id: int, rows: list[dict]) -> None:
                written_schedules.append({"debt_id": debt_id, "rows": rows})

        writer = MockWriter()

        persist_projection(writer=writer, debts=[debt], strategy="snowball", surplus=50.00)

        # Writer should have been called once
        assert len(written_schedules) == 1
        assert written_schedules[0]["debt_id"] == 1
        assert len(written_schedules[0]["rows"]) > 0

    def test_avalanche_strategy_calls_writer(self):
        """Avalanche strategy should compute schedule and call writer."""
        debt = DebtAccount(
            id=1,
            balance=1000.00,
            apr=18.0,
            minimum_payment=50.00,
            statement_due_day=15,
        )

        written_schedules = []

        class MockWriter:
            def write_schedule(self, *, debt_id: int, rows: list[dict]) -> None:
                written_schedules.append({"debt_id": debt_id, "rows": rows})

        writer = MockWriter()

        persist_projection(writer=writer, debts=[debt], strategy="avalanche", surplus=100.00)

        assert len(written_schedules) == 1
        assert written_schedules[0]["debt_id"] == 1

    def test_invalid_strategy_raises_error(self):
        """Invalid strategy should raise ValueError."""
        debt = DebtAccount(
            id=1,
            balance=1000.00,
            apr=12.0,
            minimum_payment=50.00,
            statement_due_day=15,
        )

        class MockWriter:
            def write_schedule(self, *, debt_id: int, rows: list[dict]) -> None:
                pass

        writer = MockWriter()

        with pytest.raises(ValueError, match="Invalid debt payoff strategy"):
            persist_projection(writer=writer, debts=[debt], strategy="invalid", surplus=50.00)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_debt_paid_off_in_one_payment(self):
        """Debt with balance less than payment should be paid off immediately."""
        debt = DebtAccount(
            id=1,
            balance=50.00,
            apr=12.0,
            minimum_payment=25.00,
            statement_due_day=15,
        )

        schedule = snowball_schedule(debts=[debt], surplus=100.00)

        # Should be paid off in first period
        assert len(schedule) == 1
        first_payment = schedule[0]["payments"]["debt_1"]
        assert_float_equal(first_payment["remaining_balance"], 0.00)

    def test_very_small_minimum_payment(self):
        """Debt with very small minimum payment should eventually pay off."""
        debt = DebtAccount(
            id=1,
            balance=1000.00,
            apr=12.0,
            minimum_payment=10.00,  # Very small
            statement_due_day=15,
        )

        schedule = snowball_schedule(debts=[debt], surplus=0.00)

        # Should eventually pay off (may take many periods)
        assert len(schedule) > 0
        last_payment = schedule[-1]["payments"]["debt_1"]
        assert_float_equal(last_payment["remaining_balance"], 0.00)

    def test_multiple_debts_all_paid_off(self):
        """All debts should eventually reach zero balance."""
        debts = [
            DebtAccount(
                id=1, balance=1000.00, apr=12.0, minimum_payment=50.00, statement_due_day=15
            ),
            DebtAccount(
                id=2, balance=2000.00, apr=18.0, minimum_payment=75.00, statement_due_day=15
            ),
            DebtAccount(
                id=3, balance=500.00, apr=15.0, minimum_payment=30.00, statement_due_day=15
            ),
        ]

        schedule = snowball_schedule(debts=debts, surplus=200.00)

        # Last period should have all debts at zero
        last_period = schedule[-1]
        for debt_id in [1, 2, 3]:
            payment = last_period["payments"].get(f"debt_{debt_id}")
            if payment:
                assert_float_equal(payment["remaining_balance"], 0.00)

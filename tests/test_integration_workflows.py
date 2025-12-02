"""Integration tests for multi-component workflows.

These tests verify that domain models, repositories, and services work
together correctly for realistic user scenarios.
"""

from __future__ import annotations

import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest
from pocketsage.infra.repositories.budget import SQLModelBudgetRepository
from pocketsage.infra.repositories.habit import SQLModelHabitRepository
from pocketsage.infra.repositories.liability import SQLModelLiabilityRepository
from pocketsage.infra.repositories.transaction import SQLModelTransactionRepository
from pocketsage.models.budget import Budget, BudgetLine
from pocketsage.models.habit import HabitEntry
from pocketsage.models.transaction import Transaction
from pocketsage.services.debts import DebtAccount, snowball_schedule
from pocketsage.services.import_csv import ColumnMapping, import_csv_file
from tests.conftest import assert_float_equal


@pytest.mark.integration
class TestMonthlyBudgetTracking:
    """Integration test for budget vs actual tracking workflow."""

    def test_monthly_budget_vs_actual_spending(
        self, session_factory, category_factory, transaction_factory
    ):
        """Test budget creation and actual spend tracking for a month."""
        # Setup: Create categories
        groceries = category_factory(name="Groceries", slug="groceries", category_type="expense")
        dining = category_factory(name="Dining Out", slug="dining", category_type="expense")

        # Create budget for current month
        today = date.today()
        period_start = date(today.year, today.month, 1)

        from calendar import monthrange

        last_day = monthrange(today.year, today.month)[1]
        period_end = date(today.year, today.month, last_day)

        budget_repo = SQLModelBudgetRepository(session_factory)
        uid = session_factory.user.id

        budget = Budget(
            user_id=uid,
            period_start=period_start,
            period_end=period_end,
            label="Monthly Budget",
        )

        # Add budget lines
        budget.lines = [
            BudgetLine(
                user_id=uid, category_id=groceries.id, planned_amount=500.00, budget_id=None
            ),
            BudgetLine(user_id=uid, category_id=dining.id, planned_amount=200.00, budget_id=None),
        ]

        budget_repo.create(budget, user_id=uid)

        # Add some actual transactions
        txn_repo = SQLModelTransactionRepository(session_factory)

        # Groceries: $450 (under budget)
        txn_repo.create(
            Transaction(
                user_id=uid,
                amount=-150.00,
                memo="Whole Foods",
                occurred_at=datetime(today.year, today.month, 5),
                category_id=groceries.id,
            ),
            user_id=uid,
        )
        txn_repo.create(
            Transaction(
                user_id=uid,
                amount=-300.00,
                memo="Costco",
                occurred_at=datetime(today.year, today.month, 15),
                category_id=groceries.id,
            ),
            user_id=uid,
        )

        # Dining: $250 (over budget by $50)
        txn_repo.create(
            Transaction(
                user_id=uid,
                amount=-100.00,
                memo="Restaurant",
                occurred_at=datetime(today.year, today.month, 10),
                category_id=dining.id,
            ),
            user_id=uid,
        )
        txn_repo.create(
            Transaction(
                user_id=uid,
                amount=-150.00,
                memo="Date night",
                occurred_at=datetime(today.year, today.month, 20),
                category_id=dining.id,
            ),
            user_id=uid,
        )

        # Verify budget was created with lines
        fetched_budget = budget_repo.get_for_month(today.year, today.month, user_id=uid)
        assert fetched_budget is not None
        assert len(fetched_budget.lines) == 2

        # Verify transactions were created
        all_txns = txn_repo.list_all(limit=100, user_id=uid)
        assert len(all_txns) == 4

        # Calculate actual spending by category
        summary = txn_repo.get_monthly_summary(today.year, today.month, user_id=uid)

        # All transactions are expenses (negative)
        total_expenses = summary["expenses"]
        assert_float_equal(total_expenses, 700.00)  # 450 + 250

        # In a real implementation, we'd calculate per-category actuals
        # For now, this integration test verifies the components work together


@pytest.mark.integration
class TestDebtPayoffProjection:
    """Integration test for debt payoff calculation workflow."""

    def test_multiple_debts_snowball_projection(self, session_factory, liability_factory):
        """Test creating liabilities and generating snowball payoff schedule."""
        # Create multiple debts
        credit_card = liability_factory(
            name="Credit Card",
            balance=2500.00,
            apr=22.0,
            minimum_payment=75.00,
            payoff_strategy="snowball",
        )

        car_loan = liability_factory(
            name="Car Loan",
            balance=8000.00,
            apr=6.0,
            minimum_payment=250.00,
            payoff_strategy="snowball",
        )

        student_loan = liability_factory(
            name="Student Loan",
            balance=15000.00,
            apr=4.5,
            minimum_payment=150.00,
            payoff_strategy="snowball",
        )

        # Verify liabilities were created
        liability_repo = SQLModelLiabilityRepository(session_factory)
        uid = session_factory.user.id
        all_liabilities = liability_repo.list_all(user_id=uid)
        assert len(all_liabilities) == 3

        # Calculate total debt
        total_debt = liability_repo.get_total_debt(user_id=uid)
        assert_float_equal(total_debt, 25500.00)

        # Calculate weighted average APR
        weighted_apr = liability_repo.get_weighted_apr(user_id=uid)
        expected_weighted_apr = (2500 * 22.0 + 8000 * 6.0 + 15000 * 4.5) / 25500
        assert_float_equal(weighted_apr, expected_weighted_apr)

        # Convert to DebtAccount for payoff calculation
        debts = [
            DebtAccount(
                id=liability.id,
                balance=liability.balance,
                apr=liability.apr,
                minimum_payment=liability.minimum_payment,
                statement_due_day=liability.due_day,
            )
            for liability in all_liabilities
        ]

        # Calculate snowball schedule with $500 monthly surplus
        surplus = 500.00
        schedule = snowball_schedule(debts=debts, surplus=surplus)

        # Verify schedule was generated
        assert len(schedule) > 0

        # Verify all debts are paid off by end
        last_month = schedule[-1]
        for debt_id in [credit_card.id, car_loan.id, student_loan.id]:
            payment = last_month["payments"].get(f"debt_{debt_id}")
            if payment:
                assert_float_equal(payment["remaining_balance"], 0.00)


@pytest.mark.integration
class TestHabitTrackingWorkflow:
    """Integration test for habit creation and streak tracking."""

    def test_habit_tracking_with_gaps(self, session_factory, habit_factory, db_session):
        """Test habit creation, entry tracking, and streak calculations with gaps."""
        # Create a habit
        exercise = habit_factory(
            name="Daily Exercise",
            description="30 minutes of physical activity",
            is_active=True,
        )

        habit_repo = SQLModelHabitRepository(session_factory)
        uid = session_factory.user.id

        # Track habit over 14 days with some gaps
        start_date = date.today() - timedelta(days=13)

        # Week 1: Perfect streak (7 days)
        for i in range(7):
            day = start_date + timedelta(days=i)
            entry = HabitEntry(
                habit_id=exercise.id, occurred_on=day, value=1, user_id=exercise.user_id
            )
            habit_repo.upsert_entry(entry, user_id=uid)

        # Day 8: Skipped (gap)

        # Days 9-13: Another streak (5 days)
        for i in range(8, 13):
            day = start_date + timedelta(days=i)
            entry = HabitEntry(
                habit_id=exercise.id, occurred_on=day, value=1, user_id=exercise.user_id
            )
            habit_repo.upsert_entry(entry, user_id=uid)

        # Today: Completed
        today = date.today()
        habit_repo.upsert_entry(
            HabitEntry(habit_id=exercise.id, occurred_on=today, value=1, user_id=exercise.user_id),
            user_id=uid,
        )

        # Calculate streaks
        current_streak = habit_repo.get_current_streak(exercise.id, user_id=uid)
        longest_streak = habit_repo.get_longest_streak(exercise.id, user_id=uid)

        # Current streak should be 6 (days 9-13 + today)
        assert current_streak == 6

        # Longest streak should be 7 (week 1)
        assert longest_streak == 7

        # Get all entries for verification
        all_entries = habit_repo.get_entries_for_habit(
            exercise.id,
            start_date,
            today,
            user_id=uid,
        )

        # Should have 13 entries (7 + skip + 5 + 1)
        assert len(all_entries) == 13


@pytest.mark.integration
class TestCSVImportToDatabase:
    """Integration test for CSV import to database workflow."""

    def test_csv_import_creates_transactions(
        self, session_factory, category_factory, account_factory
    ):
        """Test importing CSV file and creating transactions in database."""
        uid = session_factory.user.id
        # Setup: Create categories and accounts
        groceries = category_factory(name="Groceries", slug="groceries")
        salary = category_factory(name="Salary", slug="salary", category_type="income")
        checking = account_factory(name="Checking")

        # Create CSV file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False) as f:
            f.write("transaction_id,date,amount,description,category,account\n")
            f.write(f"TXN-001,2024-01-15,2000.00,Paycheck,{salary.id},{checking.id}\n")
            f.write(f"TXN-002,2024-01-16,-150.50,Whole Foods,{groceries.id},{checking.id}\n")
            f.write(f"TXN-003,2024-01-18,-75.25,Trader Joes,{groceries.id},{checking.id}\n")
            csv_path = Path(f.name)

        try:
            # Parse CSV (returns dict representations)
            mapping = ColumnMapping(
                amount="amount",
                occurred_at="date",
                memo="memo",
                external_id="transaction_id",
                category_id="category",
                account_id="account",
            )

            count = import_csv_file(csv_path=csv_path, mapping=mapping)
            assert count == 3

            # Now we need to actually persist to database
            # (import_csv_file just parses, doesn't persist)
            from pocketsage.services.import_csv import normalize_frame, upsert_transactions

            frame = normalize_frame(file_path=csv_path)
            rows = [dict(row) for _, row in frame.iterrows()]
            parsed_txns = upsert_transactions(rows=rows, mapping=mapping)

            # Persist using repository
            txn_repo = SQLModelTransactionRepository(session_factory)

            for txn_dict in parsed_txns:
                # Convert dict to Transaction model
                txn = Transaction(
                    user_id=uid,
                    amount=txn_dict["amount"],
                    memo=txn_dict["memo"],
                    occurred_at=datetime.fromisoformat(txn_dict["occurred_at"]),
                    external_id=txn_dict.get("external_id"),
                    category_id=txn_dict.get("category_id"),
                    account_id=txn_dict.get("account_id"),
                )
                txn_repo.create(txn, user_id=uid)

            # Verify transactions were created
            all_txns = txn_repo.list_all(limit=100, user_id=uid)
            assert len(all_txns) == 3

            # Verify external IDs were preserved (for idempotent re-import)
            external_ids = {txn.external_id for txn in all_txns}
            assert "TXN-001" in external_ids
            assert "TXN-002" in external_ids
            assert "TXN-003" in external_ids

            # Verify monthly summary
            summary = txn_repo.get_monthly_summary(2024, 1, user_id=uid)
            assert_float_equal(summary["income"], 2000.00)
            assert_float_equal(summary["expenses"], 225.75)
            assert_float_equal(summary["net"], 1774.25)

        finally:
            csv_path.unlink()


@pytest.mark.integration
class TestMultiAccountTracking:
    """Integration test for tracking transactions across multiple accounts."""

    def test_transactions_across_accounts(
        self, session_factory, account_factory, transaction_factory, category_factory
    ):
        """Test creating transactions in different accounts and querying by account."""
        uid = session_factory.user.id
        # Create multiple accounts
        checking = account_factory(name="Checking Account", currency="USD")
        savings = account_factory(name="Savings Account", currency="USD")
        credit_card = account_factory(name="Credit Card", currency="USD")

        # Create categories
        groceries = category_factory(name="Groceries", slug="groceries", category_type="expense")
        transfer = category_factory(name="Transfer", slug="transfer", category_type="income")

        # Create transactions in different accounts
        txn_repo = SQLModelTransactionRepository(session_factory)

        # Checking: Some expenses
        txn_repo.create(
            Transaction(
                user_id=uid,
                amount=-100.00,
                memo="Groceries",
                occurred_at=datetime.now(),
                account_id=checking.id,
                category_id=groceries.id,
            ),
            user_id=uid,
        )

        # Savings: Transfer in
        txn_repo.create(
            Transaction(
                user_id=uid,
                amount=500.00,
                memo="Transfer from checking",
                occurred_at=datetime.now(),
                account_id=savings.id,
                category_id=transfer.id,
            ),
            user_id=uid,
        )

        # Credit card: More expenses
        txn_repo.create(
            Transaction(
                user_id=uid,
                amount=-50.00,
                memo="Groceries",
                occurred_at=datetime.now(),
                account_id=credit_card.id,
                category_id=groceries.id,
            ),
            user_id=uid,
        )

        # Query transactions by account
        checking_txns = txn_repo.filter_by_account(checking.id, user_id=uid)
        assert len(checking_txns) == 1
        assert checking_txns[0].amount == -100.00

        savings_txns = txn_repo.filter_by_account(savings.id, user_id=uid)
        assert len(savings_txns) == 1
        assert savings_txns[0].amount == 500.00

        # Verify all transactions
        all_txns = txn_repo.list_all(limit=100, user_id=uid)
        assert len(all_txns) == 3

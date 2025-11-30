"""Heavy randomized seed helper for admin testing."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable, Optional

from sqlmodel import Session, select

from ..models import Transaction, Habit, HabitEntry, Budget, BudgetLine, Holding, Liability
from .admin_tasks import (
    SeedSummary,
    _build_seed_summary,
    _get_session,
    _heavy_transactions_seed,
    _seed_accounts,
    _seed_categories,
    _seed_habits,
    _seed_habit_entries,
    _seed_liabilities,
    _seed_liability_transactions,
    _seed_budget,
    _seed_holdings,
)

SessionFactory = Callable[[], AbstractContextManager[Session]]


def run_heavy_seed(
    session_factory: Optional[SessionFactory] = None, *, user_id: int
) -> SeedSummary:
    """Reset transactions and seed a randomized heavy dataset.

    This function clears existing data and generates fresh, randomized
    demo data including transactions, habits with completion history,
    debts, portfolio holdings, and budgets.

    Unlike run_demo_seed (which is idempotent), this function always
    regenerates all data fresh to ensure realistic, randomized patterns.
    """

    with _get_session(session_factory) as session:
        # Ensure base categories/accounts exist (idempotent)
        categories = _seed_categories(session, user_id)
        accounts = _seed_accounts(session, user_id)

        # =====================================================
        # CLEAR EXISTING DATA FOR FRESH REGENERATION
        # =====================================================
        # Order matters due to foreign key constraints:
        # 1. Clear child records before parent records
        # 2. HabitEntry before Habit
        # 3. BudgetLine before Budget

        # Clear transactions
        for tx in session.exec(select(Transaction).where(Transaction.user_id == user_id)).all():
            session.delete(tx)

        # Clear habit entries BEFORE habits (foreign key constraint)
        for entry in session.exec(select(HabitEntry).where(HabitEntry.user_id == user_id)).all():
            session.delete(entry)

        # Clear habits
        for habit in session.exec(select(Habit).where(Habit.user_id == user_id)).all():
            session.delete(habit)

        # Clear budget lines BEFORE budgets (foreign key constraint)
        for line in session.exec(select(BudgetLine).where(BudgetLine.user_id == user_id)).all():
            session.delete(line)

        # Clear budgets
        for budget in session.exec(select(Budget).where(Budget.user_id == user_id)).all():
            session.delete(budget)

        # Clear holdings
        for holding in session.exec(select(Holding).where(Holding.user_id == user_id)).all():
            session.delete(holding)

        # Clear liabilities
        for liability in session.exec(select(Liability).where(Liability.user_id == user_id)).all():
            session.delete(liability)

        session.flush()

        # =====================================================
        # GENERATE FRESH DATA
        # =====================================================

        # Generate heavy transaction dataset (5 years of realistic data)
        _heavy_transactions_seed(session, user_id, accounts)

        # Create habits and their completion history (2 years of entries)
        _seed_habits(session, user_id=user_id)
        _seed_habit_entries(session, user_id=user_id)

        # Create debt/liability data with realistic amounts
        liabilities = _seed_liabilities(session, user_id=user_id)

        # Create budgets based on actual spending patterns
        _seed_budget(session, categories, user_id=user_id)

        # Create portfolio holdings with varied allocations
        _seed_holdings(session, accounts, user_id=user_id)

        # Create liability payment transactions
        _seed_liability_transactions(
            session, liabilities, accounts, categories, user_id=user_id
        )
        session.flush()
        return _build_seed_summary(session, user_id=user_id)


__all__ = ["run_heavy_seed"]

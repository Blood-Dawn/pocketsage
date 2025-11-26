
from __future__ import annotations

from sqlmodel import select

from pocketsage.services import admin_tasks
from pocketsage.models import Transaction, Habit, Liability, Budget, BudgetLine, Holding


def test_run_demo_seed_populates_multiple_entities(session_factory):
    user_id = session_factory.user.id  # type: ignore[attr-defined]
    summary = admin_tasks.run_demo_seed(session_factory=session_factory, user_id=user_id, force=True)
    assert summary.transactions > 0
    with session_factory() as session:
        assert session.exec(select(Transaction).where(Transaction.user_id == user_id)).first() is not None
        assert len(session.exec(select(Habit).where(Habit.user_id == user_id)).all()) >= 5
        assert len(session.exec(select(Liability).where(Liability.user_id == user_id)).all()) >= 5
        assert len(session.exec(select(Budget).where(Budget.user_id == user_id)).all()) >= 1
        assert len(session.exec(select(BudgetLine).where(BudgetLine.user_id == user_id)).all()) >= 5
        assert len(session.exec(select(Holding).where(Holding.user_id == user_id)).all()) >= 5


def test_delete_data_via_reset(session_factory):
    user_id = session_factory.user.id  # type: ignore[attr-defined]
    admin_tasks.run_demo_seed(session_factory=session_factory, user_id=user_id, force=True)
    admin_tasks.reset_demo_database(user_id=user_id, session_factory=session_factory, reseed=False)
    with session_factory() as session:
        assert len(session.exec(select(Transaction).where(Transaction.user_id == user_id)).all()) == 0
        assert len(session.exec(select(Habit).where(Habit.user_id == user_id)).all()) == 0
        assert len(session.exec(select(Liability).where(Liability.user_id == user_id)).all()) == 0
        assert len(session.exec(select(Budget).where(Budget.user_id == user_id)).all()) == 0
        assert len(session.exec(select(BudgetLine).where(BudgetLine.user_id == user_id)).all()) == 0
        assert len(session.exec(select(Holding).where(Holding.user_id == user_id)).all()) == 0

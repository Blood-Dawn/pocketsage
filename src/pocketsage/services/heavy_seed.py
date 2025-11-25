"""Heavy randomized seed helper for admin testing."""

from __future__ import annotations

from contextlib import AbstractContextManager
from typing import Callable, Optional

from sqlmodel import Session, select

from ..models import Transaction
from .admin_tasks import (
    SeedSummary,
    _build_seed_summary,
    _get_session,
    _heavy_transactions_seed,
    _seed_accounts,
    _seed_categories,
)

SessionFactory = Callable[[], AbstractContextManager[Session]]


def run_heavy_seed(
    session_factory: Optional[SessionFactory] = None, *, user_id: int
) -> SeedSummary:
    """Reset transactions and seed a randomized heavy dataset."""

    with _get_session(session_factory) as session:
        # ensure base categories/accounts
        _seed_categories(session, user_id)
        accounts = _seed_accounts(session, user_id)
        # clear prior transactions for this user only
        for tx in session.exec(select(Transaction).where(Transaction.user_id == user_id)).all():
            session.delete(tx)
        session.flush()
        _heavy_transactions_seed(session, user_id, accounts)
        session.flush()
        return _build_seed_summary(session, user_id=user_id)


__all__ = ["run_heavy_seed"]

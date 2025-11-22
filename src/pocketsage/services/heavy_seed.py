"""Heavy randomized seed helper for admin testing."""

from __future__ import annotations

from typing import Optional

from sqlmodel import Session

from .admin_tasks import SeedSummary, _get_session, _seed_accounts, _seed_categories, _heavy_transactions_seed, _build_seed_summary  # type: ignore


def run_heavy_seed(session_factory: Optional[callable] = None, *, user_id: int) -> SeedSummary:
    """Reset transactions and seed a randomized heavy dataset."""

    with _get_session(session_factory) as session:  # type: ignore
        # ensure base categories/accounts
        categories = _seed_categories(session, user_id)  # type: ignore
        accounts = _seed_accounts(session, user_id)  # type: ignore
        # clear prior transactions for this user only
        from sqlmodel import select
        from ..models import Transaction

        for tx in session.exec(select(Transaction).where(Transaction.user_id == user_id)).all():
            session.delete(tx)
        session.flush()
        _heavy_transactions_seed(session, user_id, accounts)
        session.flush()
        return _build_seed_summary(session, user_id=user_id)


__all__ = ["run_heavy_seed"]

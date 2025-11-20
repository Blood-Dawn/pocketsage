from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Callable, Iterator

from pocketsage.infra.repositories import SQLModelTransactionRepository
from pocketsage.models.transaction import Transaction
from sqlmodel import Session, SQLModel, create_engine


def build_session_factory() -> Callable[[], Iterator[Session]]:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)

    @contextmanager
    def session_context():
        session = Session(engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return session_context


def seed_transactions(factory: Callable[[], Iterator[Session]], count: int = 5) -> None:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    with factory() as session:
        for idx in range(count):
            session.add(
                Transaction(
                    occurred_at=base + timedelta(days=idx),
                    amount=float(idx),
                    memo=f"Item {idx}",
                    currency="USD",
                )
            )


def test_list_all_orders_by_occurred_at_desc() -> None:
    session_factory = build_session_factory()
    seed_transactions(session_factory, count=5)

    repository = SQLModelTransactionRepository(session_factory)
    rows = repository.list_all(limit=3, offset=0)

    assert len(rows) == 3
    assert [row.memo for row in rows] == ["Item 4", "Item 3", "Item 2"]


def test_search_filters_by_date_and_text() -> None:
    session_factory = build_session_factory()
    seed_transactions(session_factory, count=4)

    repository = SQLModelTransactionRepository(session_factory)

    rows = repository.search(text="Item 2")
    assert len(rows) == 1
    assert rows[0].memo == "Item 2"

    rows = repository.search(start_date=datetime(2024, 1, 3, tzinfo=timezone.utc))
    assert len(rows) == 1
    assert rows[0].memo == "Item 3"

    rows = repository.search(end_date=datetime(2024, 1, 2, tzinfo=timezone.utc))
    assert len(rows) == 3
    assert rows[-1].memo == "Item 0"

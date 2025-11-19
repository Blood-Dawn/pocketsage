from __future__ import annotations

from datetime import datetime, timedelta, timezone

from pocketsage.blueprints.ledger.repository import SQLModelLedgerRepository
from pocketsage.models.transaction import Transaction
from sqlmodel import Session, SQLModel, create_engine


def build_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    SQLModel.metadata.create_all(engine)
    return Session(engine)


def seed_transactions(session: Session, count: int = 5) -> None:
    base = datetime(2024, 1, 1, tzinfo=timezone.utc)
    for idx in range(count):
        session.add(
            Transaction(
                occurred_at=base + timedelta(days=idx),
                amount=float(idx),
                memo=f"Item {idx}",
                currency="USD",
            )
        )
    session.commit()


def test_list_transactions_returns_total_and_page() -> None:
    session = build_session()
    try:
        seed_transactions(session, count=5)

        repository = SQLModelLedgerRepository(session=session)

        rows, total = repository.list_transactions(filters={}, page=1, per_page=2)

        assert total == 5
        assert len(rows) == 2
        assert rows[0].memo == "Item 4"
        assert rows[1].memo == "Item 3"
    finally:
        session.close()


def test_list_transactions_applies_filters() -> None:
    session = build_session()
    try:
        seed_transactions(session, count=4)

        repository = SQLModelLedgerRepository(session=session)

        rows, total = repository.list_transactions(filters={"q": "Item 2"}, page=1, per_page=10)
        assert total == 1
        assert rows[0].memo == "Item 2"

        rows, total = repository.list_transactions(
            filters={"start": "2024-01-03"}, page=1, per_page=10
        )
        assert total == 2
        assert rows[0].memo == "Item 3"
        assert rows[1].memo == "Item 2"

        rows, total = repository.list_transactions(
            filters={"end": "2024-01-02"}, page=1, per_page=10
        )
        assert total == 3
        assert rows[-1].memo == "Item 0"
    finally:
        session.close()

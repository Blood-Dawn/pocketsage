import time
from pathlib import Path

import pytest
from sqlmodel import select

from pocketsage.infra.database import create_db_engine, init_database, session_scope
from pocketsage.models import Transaction, User
from pocketsage.services import importers
from pocketsage.services.auth import create_user
from pocketsage.services.import_csv import ColumnMapping


def _make_temp_engine(tmp_path: Path):
    from pocketsage.config import BaseConfig

    cfg = BaseConfig()
    cfg.DATA_DIR = tmp_path
    cfg.DATABASE_URL = f"sqlite:///{tmp_path/'perf.db'}"
    engine = create_db_engine(cfg)
    init_database(engine)
    return engine


def _generate_csv(tmp_path: Path, rows: int = 1000) -> Path:
    path = tmp_path / "perf.csv"
    with path.open("w", encoding="utf-8") as f:
        f.write("date,amount,memo,account,category,transaction_id\n")
        for idx in range(rows):
            f.write(
                f"2024-01-01,{idx - 500:.2f},Perf {idx},Checking,Test,{idx}\n"
            )
    return path


@pytest.mark.performance
def test_import_performance(tmp_path: Path):
    """Ensure ledger import of ~1k rows completes quickly."""

    engine = _make_temp_engine(tmp_path)
    session_factory = lambda: session_scope(engine)
    user: User = create_user(
        username="perf",
        password="test",
        session_factory=session_factory,
    )
    csv_path = _generate_csv(tmp_path, rows=3000)

    start = time.perf_counter()
    created = importers.import_ledger_transactions(
        csv_path=csv_path,
        session_factory=session_factory,
        mapping=ColumnMapping(
            amount="amount",
            occurred_at="date",
            memo="memo",
            account_name="account",
            category="category",
            external_id="transaction_id",
        ),
        user_id=user.id,
    )
    elapsed = time.perf_counter() - start

    assert created > 0
    # Guardrails: keep within a reasonable bound for multi-thousand rows on dev machines
    assert elapsed < 15.0

    with session_factory() as session:
        total = session.exec(
            select(Transaction).where(Transaction.user_id == user.id)
        ).all()
    assert len(total) == created


@pytest.mark.performance
def test_pagination_cost(tmp_path: Path):
    """Ensure pagination queries stay within reasonable bounds."""

    engine = _make_temp_engine(tmp_path)
    session_factory = lambda: session_scope(engine)
    user: User = create_user(
        username="perf2",
        password="test",
        session_factory=session_factory,
    )
    csv_path = _generate_csv(tmp_path, rows=20000)
    importers.import_ledger_transactions(
        csv_path=csv_path,
        session_factory=session_factory,
        mapping=ColumnMapping(
            amount="amount",
            occurred_at="date",
            memo="memo",
            account_name="account",
            category="category",
            external_id="transaction_id",
        ),
        user_id=user.id,
    )
    start = time.perf_counter()
    with session_factory() as session:
        # Simulate pagination windows
        for offset in range(0, 20000, 500):
            _ = session.exec(
                select(Transaction)
                .where(Transaction.user_id == user.id)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
                .offset(offset)
                .limit(500)
            ).all()
    elapsed = time.perf_counter() - start
    # Guardrail: ensure we can iterate through 20k rows in slices reasonably fast
    assert elapsed < 10.0

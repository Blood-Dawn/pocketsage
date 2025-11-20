from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from pocketsage.config import BaseConfig
from pocketsage.infra.database import create_db_engine, init_database, session_scope
from pocketsage.models import Account, Holding, Transaction
from pocketsage.services import auth, importers
from sqlmodel import select


@pytest.fixture()
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "imports.db"
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    config = BaseConfig()
    engine = create_db_engine(config)
    init_database(engine)

    def base_factory():
        return session_scope(engine)

    user = auth.create_user(
        username="importer",
        password="password",
        role="admin",
        session_factory=base_factory,
    )

    def factory():
        return session_scope(engine)

    return factory, engine, user


def test_import_ledger_transactions_idempotent(session_factory, tmp_path: Path):
    factory, engine, user = session_factory

    csv_path = tmp_path / "ledger.csv"
    csv_path.write_text(
        "\n".join(
            [
                "date,amount,memo,category,account,currency,transaction_id",
                "2024-01-01,-25.00,Coffee,Coffee,Checking,USD,tx-ledger-1",
            ]
        )
    )

    created_first = importers.import_ledger_transactions(
        csv_path=csv_path, session_factory=factory, user_id=user.id
    )
    created_second = importers.import_ledger_transactions(
        csv_path=csv_path, session_factory=factory, user_id=user.id
    )

    with session_scope(engine) as session:
        txns = session.exec(select(Transaction)).all()

    assert created_first == 1
    assert created_second == 0
    assert len(txns) == 1
    assert txns[0].external_id == "tx-ledger-1"


def test_import_portfolio_updates_existing(session_factory, tmp_path: Path):
    factory, engine, user = session_factory

    csv_path = tmp_path / "portfolio.csv"
    frame = pd.DataFrame(
        [
            {
                "account": "Brokerage",
                "symbol": "AAPL",
                "shares": 10,
                "price": 150,
                "as_of": "2024-01-15",
            },
        ]
    )
    frame.to_csv(csv_path, index=False)

    first = importers.import_portfolio_holdings(
        csv_path=csv_path, session_factory=factory, user_id=user.id
    )

    # Update same holding with new values
    frame.loc[0, "shares"] = 12
    frame.loc[0, "price"] = 155
    frame.to_csv(csv_path, index=False)

    second = importers.import_portfolio_holdings(
        csv_path=csv_path, session_factory=factory, user_id=user.id
    )

    with session_scope(engine) as session:
        holdings = session.exec(select(Holding)).all()
        accounts = session.exec(select(Account)).all()

    assert first == 1
    assert second == 1  # upsert counted as processed
    assert len(holdings) == 1
    assert holdings[0].quantity == 12
    assert holdings[0].avg_price == 155
    assert len(accounts) == 1

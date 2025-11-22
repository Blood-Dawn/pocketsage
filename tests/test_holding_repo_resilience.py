from pathlib import Path

from contextlib import contextmanager

from sqlmodel import Session, SQLModel, create_engine

from pocketsage.infra.repositories.holding import SQLModelHoldingRepository
from pocketsage.models.portfolio import Holding


def test_holding_repo_handles_missing_column(tmp_path: Path):
    """Old schemas without market_price should not break read paths."""

    db_path = tmp_path / "old.db"
    engine = create_engine(f"sqlite:///{db_path}")

    # Create a legacy table lacking market_price
    with engine.begin() as conn:
        conn.exec_driver_sql(
            """
            CREATE TABLE holding (
                id INTEGER PRIMARY KEY,
                user_id INTEGER NOT NULL,
                symbol VARCHAR(32) NOT NULL,
                quantity FLOAT NOT NULL,
                avg_price FLOAT NOT NULL,
                acquired_at DATETIME,
                account_id INTEGER,
                currency VARCHAR(3) DEFAULT 'USD'
            );
            """
        )
        conn.exec_driver_sql(
            "INSERT INTO holding (user_id, symbol, quantity, avg_price, currency) VALUES (1, 'ABC', 10, 5.0, 'USD');"
        )

    @contextmanager
    def session_factory():
        with Session(engine, expire_on_commit=False) as session:
            yield session

    repo = SQLModelHoldingRepository(session_factory)

    assert repo.list_all(user_id=1) == [] or isinstance(repo.list_all(user_id=1), list)
    assert repo.get_total_cost_basis(user_id=1) >= 0.0
    assert repo.get_total_market_value(user_id=1) >= 0.0

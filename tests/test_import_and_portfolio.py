from __future__ import annotations

import io
from pathlib import Path

import pytest
from pocketsage import create_app
from pocketsage.blueprints.portfolio.repository import SqlModelPortfolioRepository
from pocketsage.extensions import session_scope
from pocketsage.models import Account, Holding, Transaction
from pocketsage.services.import_csv import ColumnMapping, import_csv_file, upsert_transactions
from sqlmodel import select


def test_upsert_transactions_parses_rows():
    rows = [
        {"amount": "-10.5", "date": "2025-01-01", "memo": "coffee", "external_id": "x1"},
        {"amount": "100", "date": "2025-01-02", "memo": "salary", "external_id": "x2"},
    ]
    mapping = ColumnMapping(
        amount="amount", occurred_at="date", memo="memo", external_id="external_id"
    )
    txs = upsert_transactions(rows=rows, mapping=mapping)
    assert len(txs) == 2
    assert txs[0]["memo"] == "coffee"


def test_import_csv_file_counts(tmp_path: Path):
    csv = tmp_path / "sample.csv"
    csv.write_text("amount,date,memo,external_id\n-10.5,2025-01-01,coffee,x1\n")
    mapping = ColumnMapping(
        amount="amount", occurred_at="date", memo="memo", external_id="external_id"
    )
    count = import_csv_file(csv_path=csv, mapping=mapping)
    assert count == 1


@pytest.fixture()
def portfolio_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "portfolio.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    app = create_app("development")
    app.testing = True
    return app


@pytest.fixture()
def portfolio_client(portfolio_app):
    with portfolio_app.test_client() as client:
        yield client


def _portfolio_csv(rows: list[dict]) -> dict:
    headers: list[str] = []
    for row in rows:
        for key in row.keys():
            if key not in headers:
                headers.append(key)
    lines = [",".join(headers)]
    for row in rows:
        lines.append(",".join(str(row.get(header, "")) for header in headers))
    content = ("\n".join(lines) + "\n").encode("utf-8")
    return {"file": (io.BytesIO(content), "positions.csv")}


def test_portfolio_import_endpoint_redirect(portfolio_client):
    resp = portfolio_client.post(
        "/portfolio/import",
        data=_portfolio_csv(
            [
                {
                    "symbol": "AAPL",
                    "quantity": "10",
                    "avg_price": "150",
                    "account": "Retirement",
                    "currency": "usd",
                    "occurred_at": "2025-01-01",
                    "amount": "1500",
                    "memo": "Initial position",
                }
            ]
        ),
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"AAPL" in resp.data
    assert b"Retirement" in resp.data
    assert b"USD" in resp.data
    assert b"Upload positions" in resp.data


def test_portfolio_import_endpoint_json(portfolio_client):
    resp = portfolio_client.post(
        "/portfolio/import",
        data=_portfolio_csv(
            [
                {
                    "symbol": "MSFT",
                    "quantity": "5",
                    "avg_price": "300",
                    "account": "Brokerage",
                    "currency": "cad",
                    "occurred_at": "2025-03-05",
                    "memo": "ETF transfer",
                }
            ]
        ),
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["imported"] == 1
    assert "redirect" in payload
    assert payload["mapping"]["account_name"] == "account"
    assert payload["mapping"]["currency"] == "currency"


def test_portfolio_export_returns_csv(portfolio_client):
    portfolio_client.post(
        "/portfolio/import",
        data=_portfolio_csv(
            [
                {
                    "symbol": "NVDA",
                    "quantity": "2.5",
                    "avg_price": "420",
                    "account": "Growth",
                    "currency": "usd",
                    "occurred_at": "2025-04-01",
                }
            ]
        ),
        content_type="multipart/form-data",
    )

    response = portfolio_client.get("/portfolio/export")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    body = response.get_data(as_text=True)
    assert "NVDA" in body
    assert "2.5" in body


def test_portfolio_import_idempotent_flow(portfolio_app, portfolio_client):
    with portfolio_app.app_context():
        with session_scope() as session:
            account = Account(name="Brokerage", currency="USD")
            session.add(account)
            session.flush()
            account_id = account.id

    first_rows = [
        {
            "symbol": "NVDA",
            "quantity": "2",
            "avg_price": "500",
            "account_id": str(account_id),
            "currency": "usd",
            "occurred_at": "2025-02-01",
            "memo": "Initial position",
        },
        {
            "symbol": "AAPL",
            "quantity": "1",
            "avg_price": "150",
            "account_id": str(account_id),
            "currency": "usd",
            "occurred_at": "2025-02-01",
        },
    ]

    portfolio_client.post(
        "/portfolio/import",
        data=_portfolio_csv(first_rows),
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )

    second_rows = [
        {
            "symbol": "NVDA",
            "quantity": "3",
            "avg_price": "500",
            "account_id": str(account_id),
            "currency": "usd",
            "occurred_at": "2025-02-02",
        }
    ]

    portfolio_client.post(
        "/portfolio/import",
        data=_portfolio_csv(second_rows),
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )

    with portfolio_app.app_context():
        with session_scope() as session:
            holdings = session.exec(select(Holding)).all()
            assert len(holdings) == 1
            holding = holdings[0]
            assert holding.symbol == "NVDA"
            assert holding.quantity == pytest.approx(3.0)
            assert holding.account_id == account_id
            assert holding.currency == "USD"

            transactions = session.exec(select(Transaction)).all()
            assert len(transactions) == 1
            tx = transactions[0]
            assert tx.account_id == account_id
            assert tx.currency == "USD"
            assert tx.amount == pytest.approx(1500.0)

            repo = SqlModelPortfolioRepository(session)
            summary = repo.allocation_summary()
            assert summary["total_value"] == pytest.approx(1500.0)
            assert summary["allocation"]["NVDA"] == pytest.approx(1.0)

from __future__ import annotations

import io
from pathlib import Path

import pytest
from pocketsage import create_app
from pocketsage.services.import_csv import ColumnMapping, import_csv_file, upsert_transactions


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


def _csv_payload(symbol: str = "AAPL", quantity: str = "10", avg_price: str = "150") -> dict:
    content = f"symbol,quantity,avg_price\n{symbol},{quantity},{avg_price}\n".encode("utf-8")
    return {"file": (io.BytesIO(content), "positions.csv")}


def test_portfolio_import_endpoint_redirect(portfolio_client):
    resp = portfolio_client.post(
        "/portfolio/import",
        data=_csv_payload(),
        content_type="multipart/form-data",
        follow_redirects=True,
    )
    assert resp.status_code == 200
    assert b"AAPL" in resp.data
    assert b"Upload positions" in resp.data


def test_portfolio_import_endpoint_json(portfolio_client):
    resp = portfolio_client.post(
        "/portfolio/import",
        data=_csv_payload("MSFT", "5", "300"),
        content_type="multipart/form-data",
        headers={"Accept": "application/json"},
    )
    assert resp.status_code == 200
    payload = resp.get_json()
    assert payload["imported"] == 1
    assert "redirect" in payload


def test_portfolio_export_returns_csv(portfolio_client):
    portfolio_client.post(
        "/portfolio/import",
        data=_csv_payload("NVDA", "2.5", "420"),
        content_type="multipart/form-data",
    )

    response = portfolio_client.get("/portfolio/export")
    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/csv")
    body = response.get_data(as_text=True)
    assert "NVDA" in body
    assert "2.5" in body

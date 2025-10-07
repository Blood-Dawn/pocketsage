from __future__ import annotations

import io
from pathlib import Path

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


def test_portfolio_import_endpoint(tmp_path: Path):
    app = create_app("development")
    app.testing = True
    client = app.test_client()

    data = {"file": (io.BytesIO(b"symbol,quantity,avg_price\nAAPL,10,150\n"), "positions.csv")}
    resp = client.post("/portfolio/import", data=data, content_type="multipart/form-data")
    # redirected to list_portfolio
    assert resp.status_code in (302, 303)

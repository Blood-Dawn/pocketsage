"""Tests for CSV export helpers and ledger export controller."""

from __future__ import annotations

import csv
from types import SimpleNamespace
from pathlib import Path

from pocketsage.services import export_csv
from pocketsage.models.transaction import Transaction


def test_export_transactions_csv_creates_file(tmp_path, transaction_factory, session_factory, user):
    """Exporting ledger data writes a CSV with header and rows."""

    output_dir = Path(tmp_path)
    txs = [
        Transaction(id=1, user_id=user.id, amount=-50.25, memo="Groceries"),
        Transaction(id=2, user_id=user.id, amount=125.00, memo="Salary"),
    ]

    output_path = output_dir / "ledger-test.csv"
    export_csv.export_transactions_csv(transactions=txs, output_path=output_path)

    assert output_path.exists(), "ledger export should create a CSV file"

    with output_path.open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    memos = {row["memo"] for row in rows}
    assert {"Groceries", "Salary"} == memos

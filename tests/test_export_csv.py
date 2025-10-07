from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from pocketsage.services.export_csv import export_transactions_csv

if TYPE_CHECKING:  # pragma: no cover
    from pocketsage.models.transaction import Transaction


def test_export_transactions_csv_empty(tmp_path: Path):
    out = tmp_path / "empty.csv"
    export_transactions_csv(transactions=[], output_path=out)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "id,occurred_at,amount,memo,external_id,category_id" in text


def test_export_transactions_csv_happy(tmp_path: Path):
    out = tmp_path / "txs.csv"
    t = cast(
        "Transaction",
        SimpleNamespace(
            id=1,
            occurred_at=datetime.now(timezone.utc),
            amount=-10.0,
            memo="coffee",
            external_id=None,
            category_id=None,
        ),
    )
    export_transactions_csv(transactions=[t], output_path=out)
    assert out.exists()
    text = out.read_text(encoding="utf-8")
    assert "coffee" in text

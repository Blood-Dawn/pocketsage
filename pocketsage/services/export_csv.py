"""CSV export helpers for PocketSage."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import Iterable

from ..models.transaction import Transaction


def _serialize_value(value):
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def export_transactions_csv(*, transactions: Iterable[Transaction], output_path: Path) -> Path:
    """Write transactions to CSV at `output_path`.

    Columns are deterministic: id, occurred_at, amount, memo, external_id, category_id.
    Returns the path written.
    """

    headers = ["id", "occurred_at", "amount", "memo", "external_id", "category_id"]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Use newline='' for csv on Windows
    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(
            fh, fieldnames=headers, extrasaction="ignore", quoting=csv.QUOTE_MINIMAL
        )
        writer.writeheader()
        for tx in transactions:
            row = {
                "id": _serialize_value(getattr(tx, "id", None)),
                "occurred_at": _serialize_value(getattr(tx, "occurred_at", None)),
                "amount": _serialize_value(getattr(tx, "amount", None)),
                "memo": _serialize_value(getattr(tx, "memo", None)),
                "external_id": _serialize_value(getattr(tx, "external_id", None)),
                "category_id": _serialize_value(getattr(tx, "category_id", None)),
            }
            writer.writerow(row)

    return output_path

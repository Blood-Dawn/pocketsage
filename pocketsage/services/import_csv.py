"""CSV ingestion utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

import pandas as pd

from ..models.transaction import Transaction


@dataclass(slots=True)
class ColumnMapping:
    """Maps expected transaction fields to CSV headers."""

    amount: str
    occurred_at: str
    memo: str | None = None
    category: str | None = None
    external_id: str | None = None

    # TODO(@imports): add currency + account columns when multi-account support ships.


def normalize_frame(*, file_path: Path, encoding: str = "utf-8") -> pd.DataFrame:
    """Load a CSV file into a DataFrame with consistent column casing."""

    frame = pd.read_csv(file_path, encoding=encoding)
    frame.columns = [c.strip().lower() for c in frame.columns]
    # TODO(@qa-team): add validation for duplicate headers and inconsistent delimiters.
    return frame


def upsert_transactions(*, rows: Iterable[Mapping], mapping: ColumnMapping) -> list[Transaction]:
    """Convert iterable of dict-like rows into Transaction objects and upsert them."""

    created: list[Transaction] = []
    for row in rows:
        # map columns conservatively; missing optional fields default to None/empty
        amount_raw = row.get(mapping.amount)
        if amount_raw is None:
            continue
        try:
            amount = float(amount_raw)
        except Exception:
            continue
        occurred_at_raw = row.get(mapping.occurred_at)
        if occurred_at_raw is None:
            continue
        try:
            occurred_at = pd.to_datetime(occurred_at_raw)
        except Exception:
            continue
        memo = row.get(mapping.memo) if mapping.memo else ""
        external = row.get(mapping.external_id) if mapping.external_id else None

        tx = Transaction(
            occurred_at=occurred_at, amount=amount, memo=memo or "", external_id=external
        )
        created.append(tx)

    # Note: this function only constructs domain objects; persistence is the caller's responsibility.
    return created


def import_csv_file(*, csv_path: Path, mapping: ColumnMapping) -> int:
    """Parse the file, create domain objects, and return number of imported rows."""

    frame = normalize_frame(file_path=csv_path)

    # Build rows as dicts using lowercase column names
    rows = []
    for _, r in frame.iterrows():
        rows.append({c: r[c] for c in frame.columns})

    mapping = mapping
    transactions = upsert_transactions(rows=rows, mapping=mapping)

    # Caller will persist; return count of parsed transaction objects
    return len(transactions)

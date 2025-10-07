"""CSV ingestion utilities."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Optional

import pandas as pd


@dataclass(slots=True)
class ColumnMapping:
    """Maps expected transaction fields to CSV headers."""

    amount: str
    occurred_at: str
    memo: str | None = None
    category: str | None = None
    external_id: str | None = None
    account_id: str | None = None
    account_name: str | None = None
    currency: str | None = None


def normalize_frame(*, file_path: Path, encoding: str = "utf-8") -> pd.DataFrame:
    """Load a CSV file into a DataFrame with consistent column casing."""

    frame = pd.read_csv(file_path, encoding=encoding)
    frame.columns = [c.strip().lower() for c in frame.columns]
    # TODO(@qa-team): add validation for duplicate headers and inconsistent delimiters.
    return frame


def upsert_transactions(*, rows: Iterable[Mapping], mapping: ColumnMapping) -> list[dict]:
    """Convert iterable of dict-like rows into plain dicts representing transactions.

    This function intentionally returns plain dictionaries to avoid importing
    ORM models during pure parsing (keeps the parser safe for unit tests).
    """

    created: list[dict] = []
    for row in rows:
        # map columns conservatively; missing optional fields default to None/empty
        amount_raw = row.get(mapping.amount)
        if amount_raw is None:
            continue
        try:
            amount = float(amount_raw)
        except Exception:
            continue

        occurred_at = row.get(mapping.occurred_at)
        memo = row.get(mapping.memo) if mapping.memo else ""
        external = row.get(mapping.external_id) if mapping.external_id else None

        account_id: Optional[int] = None
        if mapping.account_id:
            candidate = row.get(mapping.account_id)
            if candidate not in (None, ""):
                try:
                    account_id = int(candidate)
                except (TypeError, ValueError):
                    account_id = None

        account_name = None
        if mapping.account_name:
            raw_name = row.get(mapping.account_name)
            if isinstance(raw_name, str) and raw_name.strip():
                account_name = raw_name.strip()

        currency = None
        if mapping.currency:
            raw_currency = row.get(mapping.currency)
            if isinstance(raw_currency, str) and raw_currency.strip():
                currency = raw_currency.strip().upper()[:3]

        tx = {
            "occurred_at": occurred_at,
            "amount": amount,
            "memo": memo or "",
            "external_id": external,
            "category_id": row.get(mapping.category) if mapping.category else None,
        }
        if account_id is not None:
            tx["account_id"] = account_id
        if account_name:
            tx["account_name"] = account_name
        if currency:
            tx["currency"] = currency
        created.append(tx)

    # Note: this function returns plain dicts; callers may persist them using a repository/session.
    return created


def import_csv_file(*, csv_path: Path, mapping: ColumnMapping) -> int:
    """Parse the file, create domain dicts, and return number of parsed rows."""

    frame = normalize_frame(file_path=csv_path)

    # Build rows as dicts using lowercase column names
    rows: list[dict] = []
    for _, r in frame.iterrows():
        rows.append({c: r[c] for c in frame.columns})

    transactions = upsert_transactions(rows=rows, mapping=mapping)

    # Caller will persist; return count of parsed transaction dicts
    return len(transactions)

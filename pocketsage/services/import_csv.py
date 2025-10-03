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

    # TODO(@teammate): implement lookup against existing transactions + idempotent upsert logic.
    raise NotImplementedError


def import_csv_file(*, csv_path: Path, mapping: ColumnMapping) -> int:
    """Parse the file, create domain objects, and return number of imported rows."""

    # TODO(@teammate): orchestrate normalize_frame + upsert_transactions and return count.
    raise NotImplementedError

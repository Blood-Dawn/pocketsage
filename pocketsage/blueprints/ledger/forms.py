"""Ledger form stubs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class LedgerEntryForm:
    """Represents ledger entry input prior to validation."""

    occurred_at: datetime | None = None
    amount: float | None = None
    memo: str = ""
    category_id: Optional[int] = None

    def validate(self) -> bool:
        """Placeholder validation hook."""

        # TODO(@ledger-squad): integrate WTForms or Pydantic for validation.
        raise NotImplementedError

"""Ledger form validation helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional


@dataclass(slots=True)
class LedgerEntryForm:
    """Represents ledger entry input prior to validation."""

    occurred_at: datetime | None = None
    amount: float | None = None
    memo: str = ""
    category_id: Optional[int] = None
    errors: dict[str, list[str]] = field(default_factory=dict, init=False)
    raw_data: dict[str, str] = field(default_factory=dict, init=False)

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> LedgerEntryForm:
        """Create a form populated from request data."""

        form = cls()
        form.load(data)
        return form

    def load(self, data: Mapping[str, Any]) -> None:
        """Bind incoming mapping data to the form state."""

        keys = ("occurred_at", "amount", "memo", "category_id")
        self.raw_data = {}
        for key in keys:
            value = data.get(key)  # type: ignore[arg-type]
            if value is None:
                value_str = ""
            elif isinstance(value, str):
                value_str = value
            else:
                value_str = str(value)
            self.raw_data[key] = value_str

        self.memo = self.raw_data.get("memo", "").strip()

    def validate(self) -> bool:
        """Validate the bound data and populate typed attributes."""

        self.errors.clear()

        occurred_at_raw = self.raw_data.get("occurred_at", "").strip()
        self.occurred_at = None
        if not occurred_at_raw:
            self._add_error("occurred_at", "Date is required.")
        else:
            try:
                if len(occurred_at_raw) == 10:
                    self.occurred_at = datetime.strptime(occurred_at_raw, "%Y-%m-%d")
                else:
                    self.occurred_at = datetime.fromisoformat(occurred_at_raw)
            except ValueError:
                self._add_error("occurred_at", "Enter a valid date (YYYY-MM-DD).")

        amount_raw = self.raw_data.get("amount", "").strip()
        self.amount = None
        if not amount_raw:
            self._add_error("amount", "Amount is required.")
        else:
            try:
                parsed_amount = float(amount_raw)
            except (TypeError, ValueError):
                self._add_error("amount", "Enter a valid number for the amount.")
            else:
                if parsed_amount == 0:
                    self._add_error("amount", "Amount cannot be zero.")
                else:
                    self.amount = parsed_amount

        self.memo = self.memo.strip()
        if not self.memo:
            self._add_error("memo", "Memo is required.")
        elif len(self.memo) > 255:
            self._add_error("memo", "Memo must be 255 characters or fewer.")

        category_raw = self.raw_data.get("category_id", "").strip()
        self.category_id = None
        if category_raw:
            try:
                parsed_category = int(category_raw)
            except (TypeError, ValueError):
                self._add_error("category_id", "Category must be a whole number.")
            else:
                if parsed_category <= 0:
                    self._add_error(
                        "category_id", "Category must be greater than zero if provided."
                    )
                else:
                    self.category_id = parsed_category

        return not self.errors

    def _add_error(self, field: str, message: str) -> None:
        """Accumulate validation errors for a specific field."""

        self.errors.setdefault(field, []).append(message)

"""Transaction repository protocol."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Protocol

from ...models.transaction import Transaction


class TransactionRepository(Protocol):
    """Repository for managing transaction entities."""

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Retrieve a transaction by ID."""
        ...

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Transaction]:
        """List all transactions with pagination."""
        ...

    def filter_by_date_range(self, start_date: datetime, end_date: datetime) -> list[Transaction]:
        """Get transactions within a date range."""
        ...

    def filter_by_account(self, account_id: int) -> list[Transaction]:
        """Get all transactions for a specific account."""
        ...

    def filter_by_category(self, category_id: int) -> list[Transaction]:
        """Get all transactions for a specific category."""
        ...

    def search(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        text: Optional[str] = None,
    ) -> list[Transaction]:
        """Advanced search with multiple filters."""
        ...

    def create(self, transaction: Transaction) -> Transaction:
        """Create a new transaction."""
        ...

    def update(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""
        ...

    def delete(self, transaction_id: int) -> None:
        """Delete a transaction by ID."""
        ...

    def get_monthly_summary(self, year: int, month: int) -> dict[str, float]:
        """Get income/expense summary for a month."""
        ...

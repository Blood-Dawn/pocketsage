"""Holding repository protocol."""

from __future__ import annotations

from typing import Optional, Protocol

from ...models.portfolio import Holding


class HoldingRepository(Protocol):
    """Repository for managing portfolio holding entities."""

    def get_by_id(self, holding_id: int) -> Optional[Holding]:
        """Retrieve a holding by ID."""
        ...

    def get_by_symbol(self, symbol: str, account_id: Optional[int] = None) -> Optional[Holding]:
        """Retrieve a holding by symbol and optionally account."""
        ...

    def list_all(self) -> list[Holding]:
        """List all holdings."""
        ...

    def list_by_account(self, account_id: int) -> list[Holding]:
        """List holdings for a specific account."""
        ...

    def create(self, holding: Holding) -> Holding:
        """Create a new holding."""
        ...

    def update(self, holding: Holding) -> Holding:
        """Update an existing holding."""
        ...

    def delete(self, holding_id: int) -> None:
        """Delete a holding by ID."""
        ...

    def get_total_cost_basis(self, account_id: Optional[int] = None) -> float:
        """Calculate total cost basis across holdings."""
        ...

    def upsert_by_symbol(self, holding: Holding) -> Holding:
        """Insert or update a holding by symbol."""
        ...

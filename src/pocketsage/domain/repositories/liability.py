"""Liability repository protocol."""

from __future__ import annotations

from typing import Optional, Protocol

from ...models.liability import Liability


class LiabilityRepository(Protocol):
    """Repository for managing liability entities."""

    def get_by_id(self, liability_id: int) -> Optional[Liability]:
        """Retrieve a liability by ID."""
        ...

    def get_by_name(self, name: str) -> Optional[Liability]:
        """Retrieve a liability by name."""
        ...

    def list_all(self) -> list[Liability]:
        """List all liabilities."""
        ...

    def list_active(self) -> list[Liability]:
        """List liabilities with non-zero balances."""
        ...

    def create(self, liability: Liability) -> Liability:
        """Create a new liability."""
        ...

    def update(self, liability: Liability) -> Liability:
        """Update an existing liability."""
        ...

    def delete(self, liability_id: int) -> None:
        """Delete a liability by ID."""
        ...

    def get_total_debt(self) -> float:
        """Calculate total outstanding debt."""
        ...

    def get_weighted_apr(self) -> float:
        """Calculate weighted average APR across all liabilities."""
        ...

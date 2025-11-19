"""Account repository protocol."""

from __future__ import annotations

from typing import Optional, Protocol

from ...models.account import Account


class AccountRepository(Protocol):
    """Repository for managing account entities."""

    def get_by_id(self, account_id: int) -> Optional[Account]:
        """Retrieve an account by ID."""
        ...

    def get_by_name(self, name: str) -> Optional[Account]:
        """Retrieve an account by name."""
        ...

    def list_all(self) -> list[Account]:
        """List all accounts."""
        ...

    def create(self, account: Account) -> Account:
        """Create a new account."""
        ...

    def update(self, account: Account) -> Account:
        """Update an existing account."""
        ...

    def delete(self, account_id: int) -> None:
        """Delete an account by ID."""
        ...

    def get_balance(self, account_id: int) -> float:
        """Calculate current balance for an account."""
        ...

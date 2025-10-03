"""Ledger data-access abstractions."""

from __future__ import annotations

from typing import Iterable, Protocol

from ...models.transaction import Transaction


class LedgerRepository(Protocol):
    """Defines persistence operations required by ledger routes."""

    def list_transactions(
        self, *, filters: dict
    ) -> Iterable[Transaction]:  # pragma: no cover - interface
        ...

    def create_transaction(self, *, payload: dict) -> Transaction:  # pragma: no cover - interface
        ...

    def update_transaction(
        self,
        transaction_id: int,
        *,
        payload: dict,
    ) -> Transaction:  # pragma: no cover - interface
        ...


# TODO(@data-squad): implement SQLModel-backed repository adhering to protocol.

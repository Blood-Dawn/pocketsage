"""Liabilities repository contract."""

from __future__ import annotations

from typing import Iterable, Protocol

from ...models.liability import Liability


class LiabilitiesRepository(Protocol):
    """Persistence contract for liabilities."""

    def list_liabilities(self) -> Iterable[Liability]:  # pragma: no cover - interface
        ...

    def create_liability(self, *, payload: dict) -> Liability:  # pragma: no cover - interface
        ...

    def schedule_payoff(self, *, liability_id: int) -> None:  # pragma: no cover - interface
        ...


# TODO(@data-squad): provide SQL implementation and integrate debts service events.

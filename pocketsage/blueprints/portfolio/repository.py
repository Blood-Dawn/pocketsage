"""Portfolio repository contracts."""

from __future__ import annotations

from typing import Iterable, Protocol


class PortfolioRepository(Protocol):
    """Persistence operations for portfolio holdings."""

    def list_holdings(self) -> Iterable[dict]:  # pragma: no cover - interface
        ...

    def import_positions(self, *, rows: list[dict]) -> int:  # pragma: no cover - interface
        ...

    def allocation_summary(self) -> dict:  # pragma: no cover - interface
        ...


# TODO(@data-squad): implement repository bridging CSV import + storage tables.

"""Portfolio repository contracts and a simple SQLModel implementation."""

from __future__ import annotations

from typing import Iterable, List, Protocol

from sqlmodel import Session, select

from ...models import Holding


class PortfolioRepository(Protocol):
    """Persistence operations for portfolio holdings."""

    def list_holdings(self) -> Iterable[dict]:  # pragma: no cover - interface
        ...

    def import_positions(self, *, rows: List[dict]) -> int:  # pragma: no cover - interface
        ...

    def allocation_summary(self) -> dict:  # pragma: no cover - interface
        ...


class SqlModelPortfolioRepository:
    """A minimal SQLModel-backed repository implementation."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_holdings(self):
        return list(self.session.exec(select(Holding)).all())

    def import_positions(self, *, rows: List[dict]) -> int:
        created = 0
        for r in rows:
            symbol = r.get("symbol") or r.get("ticker")
            if not isinstance(symbol, str) or not symbol:
                continue
            try:
                quantity = float(r.get("quantity", 0))
                avg_price = float(r.get("avg_price", r.get("price", 0)))
            except Exception:
                continue
            h = Holding(symbol=symbol, quantity=quantity, avg_price=avg_price)
            self.session.add(h)
            created += 1
        self.session.commit()
        return created

    def allocation_summary(self) -> dict:
        rows = self.session.exec(select(Holding)).all()
        total_value = sum((h.quantity or 0) * (h.avg_price or 0) for h in rows)
        summary = {
            h.symbol: ((h.quantity or 0) * (h.avg_price or 0)) / (total_value or 1) for h in rows
        }
        return {"total_value": total_value, "allocation": summary}

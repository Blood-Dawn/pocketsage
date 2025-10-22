"""Ledger data-access abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timezone
from typing import Protocol, Sequence

from sqlalchemy import func
from sqlmodel import Session, select

from ...models.transaction import Transaction


class LedgerRepository(Protocol):
    """Defines persistence operations required by ledger routes."""

    def list_transactions(
        self, *, filters: dict, page: int, per_page: int
    ) -> tuple[Sequence[Transaction], int]:  # pragma: no cover - interface
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


@dataclass
class SQLModelLedgerRepository:
    """Ledger repository backed by a SQLModel session."""

    session: Session

    def list_transactions(
        self,
        *,
        filters: dict,
        page: int,
        per_page: int,
    ) -> tuple[list[Transaction], int]:
        """Return paginated transactions and total count matching ``filters``."""

        clauses = []

        search_term = (filters.get("q") or "").strip()
        if search_term:
            clauses.append(Transaction.memo.ilike(f"%{search_term}%"))

        start_date = _coerce_date(filters.get("start"), is_start=True)
        if start_date is not None:
            clauses.append(Transaction.occurred_at >= start_date)

        end_date = _coerce_date(filters.get("end"), is_start=False)
        if end_date is not None:
            clauses.append(Transaction.occurred_at <= end_date)

        sanitized_page = max(page, 1)
        sanitized_per_page = max(min(per_page, 100), 1)
        offset = (sanitized_page - 1) * sanitized_per_page

        count_stmt = select(func.count()).select_from(Transaction).where(*clauses)
        total = self.session.exec(count_stmt).one()

        data_stmt = (
            select(Transaction)
            .where(*clauses)
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
            .offset(offset)
            .limit(sanitized_per_page)
        )
        rows = self.session.exec(data_stmt).all()
        return rows, int(total or 0)


def _coerce_date(value: str | None, *, is_start: bool) -> datetime | None:
    """Parse a ``YYYY-MM-DD`` string into a timezone-aware datetime."""

    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            base = datetime.strptime(value, "%Y-%m-%d")
        except ValueError:
            return None
        if is_start:
            return datetime.combine(base.date(), time.min, tzinfo=timezone.utc)
        return datetime.combine(base.date(), time.max, tzinfo=timezone.utc)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    if is_start and parsed.time() == time.min:
        return datetime.combine(parsed.date(), time.min, tzinfo=parsed.tzinfo)
    if not is_start and parsed.time() == time.min:
        return datetime.combine(parsed.date(), time.max, tzinfo=parsed.tzinfo)
    return parsed


__all__ = ["LedgerRepository", "SQLModelLedgerRepository"]

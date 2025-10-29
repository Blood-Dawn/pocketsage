"""Ledger data-access abstractions."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Iterable, Protocol

from sqlalchemy import func
from sqlmodel import Session, select

from ...models.category import Category
from ...models.transaction import Transaction


class LedgerRepository(Protocol):
    """Defines persistence operations required by ledger routes."""

    def list_transactions(
        self, *, filters: dict
    ) -> Iterable[Transaction]:  # pragma: no cover - interface
        ...

    def list_categories(self) -> Iterable[Category]:  # pragma: no cover - interface
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


class SqlModelLedgerRepository:
    """SQLModel-backed ledger repository with filtering support."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_transactions(self, *, filters: dict) -> list[Transaction]:
        stmt = select(Transaction)

        start_date: date | None = filters.get("start_date")
        if start_date is not None:
            start_dt = datetime.combine(start_date, time.min)
            stmt = stmt.where(Transaction.occurred_at >= start_dt)

        end_date: date | None = filters.get("end_date")
        if end_date is not None:
            end_dt = datetime.combine(end_date, time.max).replace(microsecond=999999)
            stmt = stmt.where(Transaction.occurred_at <= end_dt)

        category_id: int | None = filters.get("category_id")
        if category_id is not None:
            stmt = stmt.where(Transaction.category_id == category_id)

        search: str | None = filters.get("search")
        if search:
            pattern = f"%{search.lower()}%"
            stmt = stmt.where(func.lower(Transaction.memo).like(pattern))

        stmt = stmt.order_by(Transaction.occurred_at.desc())
        return list(self._session.exec(stmt))

    def list_categories(self) -> list[Category]:
        stmt = select(Category).order_by(Category.name)
        return list(self._session.exec(stmt))

    def create_transaction(self, *, payload: dict) -> Transaction:  # pragma: no cover - stub
        raise NotImplementedError

    def update_transaction(
        self,
        transaction_id: int,
        *,
        payload: dict,
    ) -> Transaction:  # pragma: no cover - stub
        raise NotImplementedError

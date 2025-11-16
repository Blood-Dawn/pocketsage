"""Ledger data-access abstractions."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Iterable, Protocol

from sqlalchemy import func
from sqlmodel import Session, select

from ...models.category import Category
from ...models.transaction import Transaction


@dataclass(frozen=True, slots=True)
class LedgerSummary:
    """Aggregate cashflow metrics for a slice of ledger data."""

    inflow: float = 0.0
    outflow: float = 0.0
    net: float = 0.0


@dataclass(frozen=True, slots=True)
class LedgerPagination:
    """Pagination metadata for ledger listings."""

    page: int
    per_page: int
    total: int

    @property
    def pages(self) -> int:
        """Return the total number of pages for the current result set."""

        if self.total == 0:
            return 0
        return ceil(self.total / self.per_page)

    @property
    def has_prev(self) -> bool:
        return self.page > 1 and self.total > 0

    @property
    def has_next(self) -> bool:
        pages = self.pages
        return pages > 0 and self.page < pages

    @property
    def first_item(self) -> int:
        if self.total == 0:
            return 0
        return (self.page - 1) * self.per_page + 1

    @property
    def last_item(self) -> int:
        if self.total == 0:
            return 0
        return min(self.page * self.per_page, self.total)


@dataclass(frozen=True, slots=True)
class LedgerTransactionRow:
    """A lightweight projection of a transaction for presentation."""

    id: int
    occurred_at: datetime
    memo: str
    amount: float
    currency: str
    account_name: str | None
    category_name: str | None
    external_id: str | None


@dataclass(frozen=True, slots=True)
class LedgerListResult:
    """Container bundling transaction rows with summary + pagination."""

    transactions: Sequence[LedgerTransactionRow]
    summary: LedgerSummary
    pagination: LedgerPagination


class LedgerRepository(Protocol):
    """Defines persistence operations required by ledger routes."""

    def list_transactions(
        self,
        *,
        filters: dict,
        page: int,
        per_page: int,
    ) -> LedgerListResult:  # pragma: no cover - interface
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

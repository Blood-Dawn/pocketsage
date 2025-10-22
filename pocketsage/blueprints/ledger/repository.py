"""Ledger data-access abstractions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil
from typing import Iterable, Protocol, Sequence

from sqlalchemy import case, func
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

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
    """SQLModel-backed ledger repository used by the Flask blueprint."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_transactions(
        self,
        *,
        filters: dict,
        page: int,
        per_page: int,
    ) -> LedgerListResult:
        page = max(page, 1)
        per_page = max(per_page, 1)

        where_clauses = self._build_filters(filters)

        count_stmt = select(func.count()).select_from(Transaction)
        if where_clauses:
            count_stmt = count_stmt.where(*where_clauses)
        total = int(self.session.exec(count_stmt).one() or 0)

        stmt = (
            select(Transaction)
            .options(
                selectinload(Transaction.account),
                selectinload(Transaction.category),
            )
            .order_by(Transaction.occurred_at.desc(), Transaction.id.desc())
        )
        if where_clauses:
            stmt = stmt.where(*where_clauses)

        if total and (page - 1) * per_page >= total:
            # Clamp page to final page if the requested page exceeds bounds.
            page = ceil(total / per_page)

        offset = (page - 1) * per_page
        rows = self.session.exec(stmt.offset(offset).limit(per_page)).all()

        transactions = [self._project_transaction(txn) for txn in rows]

        summary = self._compute_summary(where_clauses)
        pagination = LedgerPagination(page=page, per_page=per_page, total=total)

        return LedgerListResult(
            transactions=transactions,
            summary=summary,
            pagination=pagination,
        )

    # internal helpers -------------------------------------------------

    def _build_filters(self, filters: dict) -> list:
        clauses: list = []
        search = (filters.get("q") or filters.get("search") or "").strip()
        if search:
            like = f"%{search.lower()}%"
            clauses.append(func.lower(Transaction.memo).like(like))

        for key, column in (
            ("category_id", Transaction.category_id),
            ("account_id", Transaction.account_id),
        ):
            value = filters.get(key)
            if value in (None, ""):
                continue
            try:
                numeric = int(value)
            except (TypeError, ValueError):
                continue
            clauses.append(column == numeric)

        return clauses

    def _project_transaction(self, txn: Transaction) -> LedgerTransactionRow:
        account_name: str | None = None
        if txn.account is not None:
            account_name = txn.account.name
        elif txn.account_id is not None:
            account_name = f"Account #{txn.account_id}"

        category_name: str | None = None
        if txn.category is not None:
            category_name = txn.category.name

        return LedgerTransactionRow(
            id=txn.id or 0,
            occurred_at=txn.occurred_at,
            memo=txn.memo or "",
            amount=float(txn.amount or 0.0),
            currency=(txn.currency or "USD").upper(),
            account_name=account_name,
            category_name=category_name,
            external_id=txn.external_id,
        )

    def _compute_summary(self, where_clauses: Iterable) -> LedgerSummary:
        inflow_case = case((Transaction.amount > 0, Transaction.amount), else_=0.0)
        outflow_case = case((Transaction.amount < 0, Transaction.amount), else_=0.0)

        summary_stmt = select(
            func.coalesce(func.sum(inflow_case), 0.0),
            func.coalesce(func.sum(outflow_case), 0.0),
        ).select_from(Transaction)

        if where_clauses:
            summary_stmt = summary_stmt.where(*where_clauses)

        inflow_raw, outflow_raw = self.session.exec(summary_stmt).one()
        inflow = float(inflow_raw or 0.0)
        outflow = abs(float(outflow_raw or 0.0))
        net = inflow - outflow

        return LedgerSummary(inflow=inflow, outflow=outflow, net=net)


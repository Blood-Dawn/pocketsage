"""Ledger-specific helpers for filtering, summaries, and persistence."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Iterable, Optional

from ..infra.repositories.transaction import SQLModelTransactionRepository
from ..models.category import Category
from ..models.transaction import Transaction


@dataclass
class LedgerFilters:
    """Filters applied to ledger listings."""

    user_id: int
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    category_id: Optional[int] = None
    text: Optional[str] = None
    txn_type: str = "all"  # income | expense | all


@dataclass
class Pagination:
    """Simple pagination parameters."""

    page: int = 1
    per_page: int = 25


def normalize_category_value(raw_value: Optional[str]) -> Optional[int]:
    """Return a nullable category id, treating falsy/'all' as None."""

    if not raw_value:
        return None
    lowered = raw_value.strip().lower()
    if lowered in {"all", "none", "any"}:
        return None
    try:
        return int(raw_value)
    except (TypeError, ValueError):
        return None


def filtered_transactions(
    repo: SQLModelTransactionRepository, filters: LedgerFilters
) -> list[Transaction]:
    """Fetch and sort transactions with the supplied filters."""

    txs = repo.search(
        start_date=filters.start_date,
        end_date=filters.end_date,
        category_id=filters.category_id,
        text=filters.text,
        user_id=filters.user_id,
    )
    if filters.txn_type == "income":
        txs = [t for t in txs if t.amount >= 0]
    elif filters.txn_type == "expense":
        txs = [t for t in txs if t.amount < 0]
    return sorted(txs, key=lambda t: t.occurred_at, reverse=True)


def paginate_transactions(
    txs: list[Transaction], pagination: Pagination
) -> tuple[list[Transaction], int]:
    """Return the current page of transactions and total count."""

    total = len(txs)
    page = max(1, pagination.page)
    per_page = max(1, pagination.per_page)
    start = (page - 1) * per_page
    end = start + per_page
    return txs[start:end], total


def compute_summary(transactions: Iterable[Transaction]) -> dict[str, float]:
    """Compute income, expenses, and net totals from the provided transactions."""

    income = sum(t.amount for t in transactions if t.amount > 0)
    expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)
    return {"income": income, "expenses": expenses, "net": income - expenses}


def compute_spending_by_category(
    transactions: Iterable[Transaction], categories: Iterable[Category]
) -> list[dict[str, object]]:
    """Roll up expense totals by category id."""

    lookup = {c.id: c.name for c in categories if c.id is not None}
    totals: dict[int | None, float] = {}
    for tx in transactions:
        if tx.amount >= 0:
            continue
        totals[tx.category_id] = totals.get(tx.category_id, 0.0) + abs(tx.amount)

    breakdown: list[dict[str, object]] = []
    for cat_id, total in totals.items():
        name = lookup.get(cat_id, "Uncategorized")
        breakdown.append({"category_id": cat_id, "name": name, "amount": total})
    breakdown.sort(key=lambda entry: entry["amount"], reverse=True)
    return breakdown


def top_categories(
    breakdown: Iterable[dict[str, object]], limit: int = 5
) -> list[dict[str, object]]:
    """Return the top N categories from a breakdown list."""

    items = list(breakdown)
    return items[:limit]


def save_transaction(
    repo: SQLModelTransactionRepository,
    *,
    existing: Transaction | None,
    amount: float,
    memo: str,
    occurred_at: datetime,
    category_id: Optional[int],
    account_id: Optional[int],
    currency: str,
    user_id: int,
) -> Transaction:
    """Centralize transaction creation/update."""

    txn = existing or Transaction()
    txn.amount = amount
    txn.memo = memo
    txn.occurred_at = occurred_at
    txn.category_id = category_id
    txn.account_id = account_id
    txn.currency = currency or "USD"
    return (
        repo.update(txn, user_id=user_id)
        if existing and txn.id
        else repo.create(txn, user_id=user_id)
    )


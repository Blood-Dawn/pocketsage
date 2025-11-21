"""Domain-level CSV import helpers for ledger and portfolio data."""

from __future__ import annotations

import math
import re
from datetime import datetime
from pathlib import Path
from typing import Callable, ContextManager, Optional

from sqlalchemy import select
from sqlmodel import Session

from ..models import Account, Category, Transaction
from ..models.portfolio import Holding
from .import_csv import ColumnMapping, load_transactions_from_csv, normalize_frame

SessionFactory = Callable[[], ContextManager[Session]]

_DEFAULT_LEDGER_MAPPING = ColumnMapping(
    amount="amount",
    occurred_at="date",
    memo="memo",
    category="category",
    account_name="account",
    currency="currency",
    external_id="transaction_id",
)


def import_ledger_transactions(
    *,
    csv_path: Path,
    session_factory: SessionFactory,
    mapping: ColumnMapping | None = None,
    user_id: int,
) -> int:
    """Parse a CSV and persist transactions, creating categories/accounts on demand."""

    mapping = mapping or _DEFAULT_LEDGER_MAPPING
    parsed_rows = load_transactions_from_csv(csv_path=csv_path, mapping=mapping)
    if not parsed_rows:
        return 0

    created = 0
    with session_factory() as session:
        for row in parsed_rows:
            occurred_at = _parse_datetime(row.get("occurred_at"))
            amount = row.get("amount")
            if occurred_at is None or amount is None:
                continue

            external_id = row.get("external_id")
            if external_id and _transaction_exists(session, str(external_id), user_id=user_id):
                continue

            category_id = _resolve_category_id(
                session,
                row.get("category_id"),
                row.get("category"),
                amount,
                user_id,
            )
            account_id = _resolve_account_id(
                session,
                row.get("account_id"),
                row.get("account_name"),
                user_id,
            )
            currency = _sanitize_currency(row.get("currency"))
            memo = str(row.get("memo") or "").strip()

            txn = Transaction(
                user_id=user_id,
                occurred_at=occurred_at,
                amount=float(amount),
                memo=memo,
                external_id=str(external_id) if external_id else None,
                category_id=category_id,
                account_id=account_id,
                currency=currency or "USD",
            )
            upserted = upsert_transaction(session, txn, user_id=user_id)
            if upserted:
                created += 1

        session.flush()

    return created


def import_portfolio_holdings(
    *, csv_path: Path, session_factory: SessionFactory, user_id: int
) -> int:
    """Parse a holdings CSV and upsert rows by symbol/account."""

    frame = normalize_frame(file_path=csv_path)
    required = {"symbol", "shares", "price"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Portfolio CSV missing columns: {', '.join(sorted(missing))}")

    processed = 0
    with session_factory() as session:
        for _, row in frame.iterrows():
            symbol = str(row.get("symbol") or "").strip().upper()
            if not symbol:
                continue

            quantity = _safe_float(row.get("shares"))
            avg_price = _safe_float(row.get("price"))
            if quantity is None or avg_price is None:
                continue

            account_name = str(row.get("account") or "").strip()
            account_id = (
                _resolve_account_id(session, row.get("account_id"), account_name, user_id)
                if account_name
                else None
            )
            currency = _sanitize_currency(row.get("currency")) or "USD"
            acquired_at = _parse_datetime(row.get("as_of"))
            market_price = _safe_float(row.get("market_price")) or 0.0

            existing = _lookup_holding(session, symbol, account_id, user_id)
            if existing:
                existing.quantity = quantity
                existing.avg_price = avg_price
                existing.acquired_at = acquired_at
                existing.currency = currency
                existing.market_price = market_price
            else:
                holding = Holding(
                    user_id=user_id,
                    symbol=symbol,
                    quantity=quantity,
                    avg_price=avg_price,
                    acquired_at=acquired_at,
                    account_id=account_id,
                    currency=currency,
                    market_price=market_price,
                )
                session.add(holding)

            processed += 1

        session.flush()

    return processed


def _parse_datetime(raw: object) -> Optional[datetime]:
    if raw in (None, ""):
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw))
    except ValueError:
        return None


def _sanitize_currency(value: object) -> Optional[str]:
    if value in (None, ""):
        return None
    text = str(value).strip().upper()
    return text[:3] if text else None


def _transaction_exists(session: Session, external_id: str, *, user_id: int) -> bool:
    statement = select(Transaction).where(
        Transaction.external_id == external_id, Transaction.user_id == user_id
    )
    return session.exec(statement).first() is not None


def upsert_transaction(session: Session, txn: Transaction, *, user_id: int) -> bool:
    """Insert or update by external_id when present; returns True if created."""

    created = False
    if txn.external_id:
        existing = session.exec(
            select(Transaction).where(
                Transaction.external_id == txn.external_id, Transaction.user_id == user_id
            )
        ).first()
        if existing:
            existing.amount = txn.amount
            existing.occurred_at = txn.occurred_at
            existing.memo = txn.memo
            existing.category_id = txn.category_id
            existing.account_id = txn.account_id
            existing.currency = txn.currency
            existing.liability_id = txn.liability_id
            session.add(existing)
        else:
            created = True
            session.add(txn)
    else:
        created = True
        session.add(txn)
    return created


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _slugify(label: str) -> str:
    cleaned = _SLUG_PATTERN.sub("-", label.strip().lower())
    cleaned = cleaned.strip("-")
    return cleaned or "uncategorized"


def _resolve_category_id(
    session: Session,
    category_id_value: object,
    category_label_value: object,
    amount: float,
    user_id: int,
) -> Optional[int]:
    if category_id_value not in (None, ""):
        try:
            candidate = int(category_id_value)
            existing = session.exec(
                select(Category).where(Category.id == candidate, Category.user_id == user_id)
            ).first()
            if existing:
                return existing.id
        except (TypeError, ValueError):
            pass

    label = str(category_label_value or "").strip()
    if not label:
        return None

    slug = _slugify(label)
    existing = session.exec(
        select(Category).where(Category.slug == slug, Category.user_id == user_id)
    ).first()
    if existing:
        return existing.id

    category = Category(
        user_id=user_id,
        name=label,
        slug=slug,
        category_type="income" if amount >= 0 else "expense",
    )
    session.add(category)
    session.flush()
    return category.id


def _resolve_account_id(
    session: Session, account_id_value: object, account_name_value: object, user_id: int
) -> Optional[int]:
    # Prefer explicit numeric account_id
    if account_id_value not in (None, ""):
        try:
            candidate = int(account_id_value)
            existing = session.exec(
                select(Account).where(Account.id == candidate, Account.user_id == user_id)
            ).first()
            if existing:
                return existing.id
        except (TypeError, ValueError):
            pass

    name = str(account_name_value or "").strip()
    if not name:
        return None

    existing = session.exec(
        select(Account).where(Account.name == name, Account.user_id == user_id)
    ).scalar_one_or_none()
    if existing:
        return existing.id

    account = Account(name=name, currency="USD", user_id=user_id)
    session.add(account)
    session.flush()
    return account.id


def _lookup_holding(
    session: Session, symbol: str, account_id: Optional[int], user_id: int
) -> Optional[Holding]:
    statement = select(Holding).where(Holding.symbol == symbol, Holding.user_id == user_id)
    if account_id is None:
        statement = statement.where(Holding.account_id.is_(None))
    else:
        statement = statement.where(Holding.account_id == account_id)
    return session.exec(statement).scalar_one_or_none()


def _safe_float(value: object) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if math.isnan(number):
        return None
    return number

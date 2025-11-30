"""Domain-level CSV import helpers for ledger and portfolio data."""
# TODO(@pocketsage-ledger): Guarantee idempotent import by external_id and write tests.

from __future__ import annotations

import csv
import hashlib
import logging
import math
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, ContextManager, Optional, cast

from sqlalchemy import func
from sqlmodel import Session, select

from ..models import Account, Category, Transaction
from ..models.portfolio import Holding
from .import_csv import ColumnMapping, load_transactions_from_csv, normalize_frame

logger = logging.getLogger(__name__)

SessionFactory = Callable[[], ContextManager[Session]]
ACCOUNT_ID_COLUMN = cast(Any, Account.id)
ACCOUNT_NAME_COLUMN = cast(Any, Account.name)
HOLDING_ACCOUNT_COLUMN = cast(Any, Holding.account_id)


from dataclasses import dataclass


@dataclass
class ImportResult:
    """Result of an import operation."""
    created: int
    skipped: int
    errors: list[str]


def import_transactions(
    csv_path: Path,
    session: Session,
    user_id: int,
    *,
    account_id: int | None = None,
    category_map: dict[str, int] | None = None,
) -> ImportResult:
    """Import transactions from CSV file with robust column detection and logging."""

    created = 0
    skipped = 0
    errors: list[str] = []

    logger.info(f"Starting transaction import from: {csv_path}")

    try:
        with csv_path.open("r", newline="", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)

            headers = reader.fieldnames or []
            logger.info(f"CSV headers found: {headers}")

            if not headers:
                errors.append("CSV file has no headers")
                return ImportResult(created=0, skipped=0, errors=errors)

            row_count = 0
            for row_num, row in enumerate(reader, start=2):
                row_count += 1

                if row_num <= 4:
                    logger.info(f"Row {row_num} data: {dict(row)}")

                try:
                    # Extract date with multiple column name support
                    date_str = (
                        row.get("date")
                        or row.get("Date")
                        or row.get("DATE")
                        or row.get("occurred_at")
                        or row.get("transaction_date")
                        or row.get("Transaction Date")
                    )

                    if not date_str:
                        errors.append(f"Row {row_num}: No date found. Columns: {list(row.keys())}")
                        skipped += 1
                        continue

                    # Parse date with multiple format support
                    parsed_date = None
                    date_str = date_str.strip()

                    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d", "%m-%d-%Y", "%d-%m-%Y"]:
                        try:
                            parsed_date = datetime.strptime(date_str, fmt)
                            break
                        except ValueError:
                            continue

                    if parsed_date is None:
                        if "T" in date_str:
                            try:
                                parsed_date = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                            except Exception:
                                pass

                    if parsed_date is None:
                        errors.append(f"Row {row_num}: Could not parse date '{date_str}'")
                        skipped += 1
                        continue

                    # Extract amount
                    amount_str = (
                        row.get("amount")
                        or row.get("Amount")
                        or row.get("AMOUNT")
                        or row.get("value")
                        or row.get("Value")
                        or row.get("transaction_amount")
                    )

                    if not amount_str:
                        errors.append(f"Row {row_num}: No amount found")
                        skipped += 1
                        continue

                    try:
                        clean_amount = str(amount_str).replace("$", "").replace(",", "").replace(" ", "").strip()
                        # Handle parentheses for negative: (100.00) -> -100.00
                        if clean_amount.startswith("(") and clean_amount.endswith(")"):
                            clean_amount = "-" + clean_amount[1:-1]
                        amount = float(clean_amount)
                    except (ValueError, TypeError) as amt_exc:
                        errors.append(f"Row {row_num}: Could not parse amount '{amount_str}'")
                        skipped += 1
                        continue

                    # Extract memo/description
                    memo = (
                        row.get("memo")
                        or row.get("Memo")
                        or row.get("MEMO")
                        or row.get("description")
                        or row.get("Description")
                        or row.get("DESCRIPTION")
                        or row.get("note")
                        or row.get("Note")
                        or row.get("Payee")
                        or row.get("payee")
                        or ""
                    )
                    if memo:
                        memo = str(memo).strip()

                    # Extract or generate external_id
                    external_id = (
                        row.get("external_id")
                        or row.get("id")
                        or row.get("transaction_id")
                        or row.get("reference")
                    )

                    if not external_id:
                        # Include row_num and filename in hash for uniqueness
                        hash_input = f"{csv_path.name}|{row_num}|{date_str}|{amount}|{memo}"
                        external_id = f"import-{hashlib.md5(hash_input.encode()).hexdigest()[:16]}"

                    # Check for existing transaction
                    existing = session.exec(
                        select(Transaction).where(
                            Transaction.external_id == external_id,
                            Transaction.user_id == user_id,
                        )
                    ).first()

                    if existing:
                        logger.debug(f"Row {row_num}: Skipping duplicate (external_id={external_id})")
                        skipped += 1
                        continue

                    # Resolve category
                    category_id = None
                    category_str = (
                        row.get("category")
                        or row.get("Category")
                        or row.get("CATEGORY")
                        or row.get("category_id")
                        or row.get("category_name")
                    )

                    if category_str:
                        category_str = str(category_str).strip()
                        if category_map and category_str in category_map:
                            category_id = category_map[category_str]
                        else:
                            cat = session.exec(
                                select(Category).where(
                                    Category.name == category_str,
                                    Category.user_id == user_id,
                                )
                            ).first()
                            if cat:
                                category_id = cat.id
                            else:
                                # Case-insensitive fallback
                                cat = session.exec(
                                    select(Category).where(
                                        func.lower(Category.name) == category_str.lower(),
                                        Category.user_id == user_id,
                                    )
                                ).first()
                                if cat:
                                    category_id = cat.id

                    # Resolve account
                    resolved_account_id = account_id
                    account_str = (
                        row.get("account")
                        or row.get("Account")
                        or row.get("ACCOUNT")
                        or row.get("account_id")
                        or row.get("account_name")
                    )

                    if account_str and not account_id:
                        account_str = str(account_str).strip()
                        acc = session.exec(
                            select(Account).where(
                                Account.name == account_str,
                                Account.user_id == user_id,
                            )
                        ).first()
                        if acc:
                            resolved_account_id = acc.id

                    # Create transaction
                    tx = Transaction(
                        user_id=user_id,
                        external_id=external_id,
                        occurred_at=parsed_date,
                        amount=amount,
                        memo=memo,
                        category_id=category_id,
                        account_id=resolved_account_id,
                        currency="USD",
                    )

                    session.add(tx)
                    created += 1

                except Exception as row_exc:
                    errors.append(f"Row {row_num}: {row_exc}")
                    skipped += 1

            logger.info(f"Import complete: {row_count} rows processed, {created} created, {skipped} skipped")

            if created > 0:
                session.flush()

    except Exception as file_exc:
        logger.error(f"Import failed: {file_exc}")
        errors.append(f"File error: {file_exc}")

    return ImportResult(created=created, skipped=skipped, errors=errors)


_DEFAULT_LEDGER_MAPPING = ColumnMapping(
    amount="amount",
    occurred_at="date",
    memo="memo",
    category="category",
    account_name="account",
    currency="currency",
    external_id="transaction_id",
    transaction_type="transaction_type",
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
    seen_digests: set[str] = set()
    with session_factory() as session:
        for row in parsed_rows:
            occurred_at = _parse_datetime(row.get("occurred_at"))
            amount = row.get("amount")
            if occurred_at is None or amount is None:
                continue

            amount_val = float(amount)
            memo = str(row.get("memo") or "").strip()

            # Handle transaction type to determine amount sign
            # Transaction model uses: positive for income, negative for expense
            transaction_type = str(row.get("transaction_type") or "").strip().lower()
            if transaction_type:
                # If type is specified, ensure amount has correct sign
                if transaction_type in ("expense", "debit", "withdrawal", "payment"):
                    amount_val = -abs(amount_val)
                elif transaction_type in ("income", "credit", "deposit"):
                    amount_val = abs(amount_val)
                # Otherwise keep amount as-is (might be transfer or other type)
            # If no type specified, keep amount sign from CSV (existing behavior)

            external_id = str(row.get("external_id") or "").strip()
            if not external_id:
                external_id = _row_digest(
                    occurred_at=occurred_at,
                    amount=amount_val,
                    memo=memo,
                    category=row.get("category"),
                    account=row.get("account_name"),
                )
            if external_id and _transaction_exists(session, str(external_id), user_id=user_id):
                continue
            if external_id in seen_digests:
                continue
            seen_digests.add(external_id)

            category_id = _resolve_category_id(
                session,
                row.get("category_id"),
                row.get("category"),
                amount_val,
                user_id,
            )
            account_id = _resolve_account_id(
                session,
                row.get("account_id"),
                row.get("account_name"),
                user_id,
            )
            currency = _sanitize_currency(row.get("currency"))

            txn = Transaction(
                user_id=user_id,
                occurred_at=occurred_at,
                amount=amount_val,
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
    column_aliases = {
        "quantity": "shares",
        "avg_price": "price",
    }
    for src, dest in column_aliases.items():
        if src in frame.columns and dest not in frame.columns:
            frame = frame.rename(columns={src: dest})

    required = {"symbol", "shares", "price"}
    missing = required - set(frame.columns)
    if missing:
        raise ValueError(f"Portfolio CSV missing columns: {', '.join(sorted(missing))}")

    processed = 0
    seen_digests: set[str] = set()
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
            digest = _row_digest(
                occurred_at=acquired_at or datetime.min,
                amount=quantity * avg_price,
                memo=symbol,
                category=account_name,
                account=row.get("account_id"),
            )
            if digest in seen_digests:
                continue
            seen_digests.add(digest)

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


def _row_digest(
    *, occurred_at: datetime, amount: float, memo: str, category: object, account: object
) -> str:
    """Compute a stable hash for idempotent imports when no external_id is provided."""

    parts = [
        occurred_at.strftime("%Y-%m-%d"),
        f"{amount:.2f}",
        memo.strip().lower(),
        str(category or "").strip().lower(),
        str(account or "").strip().lower(),
    ]
    data = "|".join(parts).encode("utf-8")
    return hashlib.md5(data).hexdigest()


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
    category_candidate = _safe_int(category_id_value)
    if category_candidate is not None:
        existing = session.exec(
            select(Category).where(Category.id == category_candidate, Category.user_id == user_id)
        ).first()
        if existing:
            return existing.id

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
    account_candidate = _safe_int(account_id_value)
    if account_candidate is not None:
        existing = session.exec(
            select(Account).where(
                ACCOUNT_ID_COLUMN == account_candidate, Account.user_id == user_id
            )
        ).first()
        if existing:
            return existing.id

    name = str(account_name_value or "").strip()
    if not name:
        return None

    existing = session.exec(
        select(Account).where(ACCOUNT_NAME_COLUMN == name, Account.user_id == user_id)
    ).first()
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
        statement = statement.where(HOLDING_ACCOUNT_COLUMN.is_(None))
    else:
        statement = statement.where(HOLDING_ACCOUNT_COLUMN == account_id)
    return session.exec(statement).first()


def _safe_float(value: object) -> Optional[float]:
    if value in (None, ""):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(number) else number


def _safe_int(value: object) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None

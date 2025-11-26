"""Admin utilities for the desktop app (demo seed, exports, retention)."""
# TODO(@pocketsage-admin): Support light vs heavy seed profiles and measure seed performance.
# TODO(@pocketsage-admin): Add safety checks before destructive reset operations.

# TODO(@codex): Admin service functions for data management
#    - Demo data seeding (run_demo_seed) - creates sample data (DONE)
#    - Backup export (backup_database) - exports all data to zip (DONE)
#    - Restore from backup (restore_database) - imports from zip (DONE)
#    - Reset database (reset_demo_database) - clears user data (DONE)
#    - Export reports (run_export) - generates charts and CSVs (DONE)
#    - Ensure idempotent seeding (no duplicates on re-run)
#    - Log operations for debugging

from __future__ import annotations

import os
from calendar import monthrange
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterator, Optional
from zipfile import ZipFile

from sqlalchemy import func
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, select

from ..config import BaseConfig
from ..infra.database import create_db_engine, init_database
from ..infra.database import session_scope as infra_session_scope
from ..models import (
    Account,
    Budget,
    BudgetLine,
    Category,
    Habit,
    HabitEntry,
    Holding,
    Liability,
    Transaction,
)
from .export_csv import export_transactions_csv
from .reports import export_spending_png

SessionFactory = Callable[[], AbstractContextManager[Session]]

_ENGINE = None


@dataclass(frozen=True)
class SeedSummary:
    """Aggregate counts returned after demo seeding."""

    transactions: int
    categories: int
    accounts: int
    habits: int
    liabilities: int
    budgets: int


def _get_engine():
    """Initialize and cache the SQLModel engine for background tasks."""

    global _ENGINE
    if _ENGINE is None:
        config = BaseConfig()
        _ENGINE = create_db_engine(config)
        init_database(_ENGINE)
    return _ENGINE


@contextmanager
def _get_session(session_factory: Optional[SessionFactory] = None) -> Iterator[Session]:
    """Yield a session from the provided factory or the shared engine."""

    if session_factory is not None:
        with session_factory() as session:
            yield session
        return

    engine = _get_engine()
    with infra_session_scope(engine) as session:
        yield session


def _resolve_engine(session_factory: Optional[SessionFactory]) -> Engine:
    """Resolve the engine used by the provided session factory if possible."""

    if session_factory is None:
        return _get_engine()

    with session_factory() as session:
        bind = session.get_bind()
        if bind is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Session is not bound to an engine")
        if isinstance(bind, Connection):
            return bind.engine
        if isinstance(bind, Engine):
            return bind
        raise RuntimeError(f"Unsupported bind type: {type(bind)!r}")


def _seed_categories(session: Session, user_id: int) -> dict[str, Category]:
    # Core set aligns with dashboards/graphs and heavy seed generator.
    categories_seed = [
        # Expenses
        {"name": "Groceries", "slug": "groceries", "category_type": "expense", "color": "#4CAF50"},
        {"name": "Dining Out", "slug": "dining-out", "category_type": "expense", "color": "#FF7043"},
        {"name": "Rent", "slug": "rent", "category_type": "expense", "color": "#8D6E63"},
        {"name": "Utilities", "slug": "utilities", "category_type": "expense", "color": "#29B6F6"},
        {"name": "Internet", "slug": "internet", "category_type": "expense", "color": "#0277BD"},
        {"name": "Phone", "slug": "phone", "category_type": "expense", "color": "#5C6BC0"},
        {"name": "Gas", "slug": "gas", "category_type": "expense", "color": "#AB47BC"},
        {"name": "Transit", "slug": "transit", "category_type": "expense", "color": "#7E57C2"},
        {"name": "Medical", "slug": "medical", "category_type": "expense", "color": "#C62828"},
        {"name": "Subscriptions", "slug": "subscriptions", "category_type": "expense", "color": "#6D4C41"},
        {"name": "Gaming", "slug": "gaming", "category_type": "expense", "color": "#9C27B0"},
        {"name": "Clothing", "slug": "clothing", "category_type": "expense", "color": "#8E24AA"},
        {"name": "Gifts", "slug": "gifts", "category_type": "expense", "color": "#D81B60"},
        {"name": "Travel", "slug": "travel", "category_type": "expense", "color": "#00897B"},
        {"name": "Education", "slug": "education", "category_type": "expense", "color": "#039BE5"},
        {"name": "Pets", "slug": "pets", "category_type": "expense", "color": "#6D4C41"},
        {"name": "Household", "slug": "household", "category_type": "expense", "color": "#9E9D24"},
        {"name": "Entertainment", "slug": "entertainment", "category_type": "expense", "color": "#F4511E"},
        {"name": "Coffee", "slug": "coffee", "category_type": "expense", "color": "#795548"},
        {"name": "Wellness", "slug": "wellness", "category_type": "expense", "color": "#8D6E63"},
        # Income / transfers
        {"name": "Salary", "slug": "salary", "category_type": "income", "color": "#2E7D32"},
        {"name": "Bonus", "slug": "bonus", "category_type": "income", "color": "#4CAF50"},
        {"name": "Interest", "slug": "interest", "category_type": "income", "color": "#1B5E20"},
        {"name": "Dividends", "slug": "dividends", "category_type": "income", "color": "#00796B"},
        {"name": "Refund", "slug": "refund", "category_type": "income", "color": "#558B2F"},
        {"name": "Transfer In", "slug": "transfer-in", "category_type": "income", "color": "#00796B"},
        {"name": "Transfer Out", "slug": "transfer-out", "category_type": "expense", "color": "#00838F"},
        {"name": "Payment", "slug": "payment", "category_type": "expense", "color": "#AD1457"},
        {"name": "Rebalance", "slug": "rebalance", "category_type": "income", "color": "#00695C"},
    ]
    categories: dict[str, Category] = {}
    for payload in categories_seed:
        existing = session.exec(
            select(Category).where(Category.slug == payload["slug"], Category.user_id == user_id)
        ).first()
        if existing:
            categories[payload["slug"]] = existing
            continue
        category = Category(user_id=user_id, **payload)
        session.add(category)
        session.flush()
        categories[payload["slug"]] = category
    session.flush()
    return categories


def _seed_accounts(session: Session, user_id: int) -> dict[str, Account]:
    accounts_seed = [
        {"name": "Everyday Checking", "currency": "USD", "account_type": "checking", "balance": 2500},
        {"name": "Rainy Day Savings", "currency": "USD", "account_type": "savings", "balance": 5000},
        {"name": "Travel Card", "currency": "USD", "account_type": "credit", "balance": -800},
        {"name": "Brokerage", "currency": "USD", "account_type": "investment", "balance": 12000},
    ]
    accounts: dict[str, Account] = {}
    for payload in accounts_seed:
        existing = session.exec(
            select(Account).where(Account.name == payload["name"], Account.user_id == user_id)
        ).first()
        if existing:
            accounts[payload["name"]] = existing
            continue
        account = Account(user_id=user_id, **payload)
        session.add(account)
        session.flush()
        accounts[payload["name"]] = account
    session.flush()
    return accounts


def _seed_transactions(
    session: Session,
    categories: dict[str, Category],
    accounts: dict[str, Account],
    user_id: int,
) -> None:
    now = datetime.now(timezone.utc)
    transaction_specs = [
        {
            "external_id": "demo-tx-001",
            "occurred_at": datetime(2024, 1, 5, 13, 30, tzinfo=timezone.utc),
            "amount": -58.23,
            "memo": "Grocery Run",
            "category_slug": "groceries",
        },
        {
            "external_id": "demo-tx-002",
            "occurred_at": datetime(2024, 1, 8, 19, 45, tzinfo=timezone.utc),
            "amount": -32.5,
            "memo": "Dinner with friends",
            "category_slug": "dining-out",
        },
        {
            "external_id": "demo-tx-003",
            "occurred_at": datetime(2024, 1, 10, 8, 0, tzinfo=timezone.utc),
            "amount": -90.0,
            "memo": "Electric bill",
            "category_slug": "utilities",
        },
        {
            "external_id": "demo-tx-004",
            "occurred_at": datetime(2024, 1, 15, 12, 0, tzinfo=timezone.utc),
            "amount": 2800.0,
            "memo": "Monthly salary",
            "category_slug": "salary",
        },
        {
            "external_id": "seed-salary-001",
            "occurred_at": now,
            "amount": 1500.0,
            "memo": "Salary",
            "category_slug": "salary",
        },
        {
            "external_id": "seed-coffee-001",
            "occurred_at": now,
            "amount": -4.50,
            "memo": "Coffee",
            "category_slug": "coffee",
        },
    ]

    account = accounts["Everyday Checking"]

    for spec in transaction_specs:
        existing = session.exec(
            select(Transaction).where(
                Transaction.external_id == spec["external_id"], Transaction.user_id == user_id
            )
        ).one_or_none()
        category_id = categories[spec["category_slug"]].id
        if category_id is None or account.id is None:
            continue
        if existing is None:
            existing = Transaction(
                user_id=user_id,
                external_id=spec["external_id"],
                occurred_at=spec["occurred_at"],
                amount=spec["amount"],
                memo=spec["memo"],
                category_id=category_id,
                account_id=account.id,
                currency=account.currency,
            )
            session.add(existing)
        else:
            existing.occurred_at = spec["occurred_at"]
            existing.amount = spec["amount"]
            existing.memo = spec["memo"]
            existing.category_id = category_id
            existing.account_id = account.id
            existing.currency = account.currency
            existing.user_id = user_id


def _heavy_transactions_seed(session: Session, user_id: int, accounts: dict[str, Account]) -> None:
    """Generate a randomized heavy transaction dataset for testing."""

    import random
    from datetime import timedelta

    start_date = datetime(2015, 1, 1, tzinfo=timezone.utc)
    end_date = datetime(2025, 1, 1, tzinfo=timezone.utc)
    income_categories = ["Salary", "Bonus", "Interest", "Dividends", "Refund"]
    expense_categories = [
        "Groceries",
        "Dining Out",
        "Rent",
        "Utilities",
        "Internet",
        "Phone",
        "Gas",
        "Transit",
        "Medical",
        "Subscriptions",
        "Gaming",
        "Clothing",
        "Gifts",
        "Travel",
        "Education",
        "Pets",
        "Household",
        "Entertainment",
    ]
    transfer_categories = ["Transfer In", "Transfer Out", "Payment", "Rebalance"]
    merchants = [
        "Amazon",
        "Walmart",
        "Target",
        "Steam",
        "Netflix",
        "Spotify",
        "Hulu",
        "Uber",
        "Lyft",
        "Publix",
        "Aldi",
        "Costco",
        "Shell",
        "Chevron",
        "Local Cafe",
        "Electric Co",
        "Water & Sewer",
        "Mobile Carrier",
        "Gym",
        "Bookstore",
        "Pharmacy",
        "Airline",
        "Hotel",
        "GameStop",
    ]

    # ensure base categories exist
    category_cache: dict[str, Category] = {}
    for name in income_categories + expense_categories + transfer_categories:
        slug = name.lower().replace(" ", "-")
        existing = session.exec(
            select(Category).where(Category.slug == slug, Category.user_id == user_id)
        ).first()
        if not existing:
            existing = Category(
                user_id=user_id,
                name=name,
                slug=slug,
                category_type="income" if name in income_categories else "expense",
            )
            session.add(existing)
            session.flush()
        category_cache[name] = existing

    account_ids = [acct.id for acct in accounts.values() if acct.id]
    balances = {aid: random.uniform(500, 4000) for aid in account_ids}

    current_date = start_date
    txn_idx = 1
    rows: list[Transaction] = []
    while current_date < end_date:
        for _ in range(random.randint(0, 6)):
            roll = random.random()
            if roll < 0.15:
                category_name = random.choice(income_categories)
                amount = round(random.uniform(200, 3000), 2)
            elif roll < 0.75:
                category_name = random.choice(expense_categories)
                amount = round(-random.uniform(5, 400), 2)
            else:
                category_name = random.choice(transfer_categories)
                amount = round(random.uniform(50, 1500), 2)
                if random.random() < 0.5:
                    amount = -amount

            account_id = random.choice(account_ids)
            balances[account_id] = balances.get(account_id, 0) + amount
            merchant = random.choice(merchants)
            memo = f"{category_name} - {merchant}"
            rows.append(
                Transaction(
                    user_id=user_id,
                    occurred_at=current_date,
                    amount=amount,
                    memo=memo,
                    external_id=f"heavy-{txn_idx}",
                    category_id=category_cache[category_name].id,
                    account_id=account_id,
                    currency="USD",
                )
            )
            txn_idx += 1
        current_date += timedelta(days=1)

    session.add_all(rows)
    session.flush()


def _seed_habits(session: Session, user_id: int) -> None:
    habit_specs = [
        {
            "name": "Morning Run",
            "description": "Run at least 2 miles before work.",
            "cadence": "daily",
            "entries": [
                (date(2024, 1, 6), 1),
                (date(2024, 1, 7), 0),
                (date(2024, 1, 8), 1),
            ],
        },
        {
            "name": "Review Budget",
            "description": "Check spending against the monthly plan.",
            "cadence": "weekly",
            "entries": [
                (date(2024, 1, 5), 1),
                (date(2024, 1, 12), 1),
            ],
        },
    ]

    for spec in habit_specs:
        existing = session.exec(
            select(Habit).where(Habit.name == spec["name"], Habit.user_id == user_id)
        ).one_or_none()
        if existing is None:
            existing = Habit(
                user_id=user_id,
                name=spec["name"],
                description=spec["description"],
                cadence=spec["cadence"],
            )
            session.add(existing)
            session.flush()
        else:
            existing.description = spec["description"]
            existing.cadence = spec["cadence"]
            if not existing.is_active:
                existing.is_active = True

        if existing.id is None:
            session.flush()
        if existing.id is None:
            continue

        entries = {
            entry.occurred_on: entry
            for entry in session.exec(
                select(HabitEntry).where(
                    HabitEntry.habit_id == existing.id, HabitEntry.user_id == user_id
                )
            ).all()
        }
        for occurred_on, value in spec["entries"]:
            entry = entries.get(occurred_on)
            if entry is None:
                session.add(
                    HabitEntry(
                        user_id=user_id,
                        habit_id=existing.id,
                        occurred_on=occurred_on,
                        value=value,
                    )
                )
            else:
                entry.value = value


def _seed_liabilities(session: Session, user_id: int) -> None:
    liability_specs = [
        {
            "name": "Student Loan",
            "balance": 12500.0,
            "apr": 4.5,
            "minimum_payment": 150.0,
            "due_day": 15,
        },
        {
            "name": "Credit Card",
            "balance": 2300.0,
            "apr": 19.99,
            "minimum_payment": 65.0,
            "due_day": 10,
        },
    ]

    for spec in liability_specs:
        existing = session.exec(
            select(Liability).where(Liability.name == spec["name"], Liability.user_id == user_id)
        ).one_or_none()
        if existing is None:
            session.add(Liability(user_id=user_id, **spec))
        else:
            existing.balance = spec["balance"]
            existing.apr = spec["apr"]
            existing.minimum_payment = spec["minimum_payment"]
            existing.due_day = spec["due_day"]


def _seed_budget(session: Session, categories: dict[str, Category], user_id: int) -> None:
    now = datetime.now(timezone.utc)
    period_start = date(now.year, now.month, 1)
    period_end = date(now.year, now.month, monthrange(now.year, now.month)[1])
    existing_budget = session.exec(
        select(Budget).where(
            Budget.period_start == period_start,
            Budget.period_end == period_end,
            Budget.user_id == user_id,
        )
    ).one_or_none()
    if existing_budget is None:
        budget = Budget(
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
            label=f"{now.strftime('%B %Y')} Demo Budget",
        )
        session.add(budget)
        session.flush()
        existing_budget = budget
    if existing_budget.id is None:
        session.flush()
    if existing_budget.id is None:
        return

    coffee_category = categories.get("coffee")
    if coffee_category:
        existing_line = session.exec(
            select(BudgetLine).where(
                BudgetLine.budget_id == existing_budget.id,
                BudgetLine.category_id == coffee_category.id,
                BudgetLine.user_id == user_id,
            )
        ).one_or_none()
        if existing_line is None:
            session.add(
                BudgetLine(
                    user_id=user_id,
                    budget_id=existing_budget.id,
                    category_id=coffee_category.id,
                    planned_amount=50.0,
                    rollover_enabled=False,
                )
            )


def reset_demo_database(
    user_id: int, session_factory: Optional[SessionFactory] = None, reseed: bool = True
) -> SeedSummary:
    """Reset demo data for a specific user."""

    # Guard against accidental cross-user resets
    with _get_session(session_factory) as session:
        models = (
            Transaction,
            BudgetLine,
            Budget,
            HabitEntry,
            Habit,
            Liability,
            Holding,
            Account,
            Category,
        )
        for model in models:
            rows = session.exec(select(model).where(getattr(model, "user_id") == user_id)).all()  # type: ignore[attr-defined]
            for row in rows:
                session.delete(row)
        session.commit()
    if reseed:
        return run_demo_seed(session_factory=session_factory, user_id=user_id, force=True)
    return SeedSummary(transactions=0, categories=0, accounts=0, habits=0, liabilities=0, budgets=0)


def run_demo_seed(
    session_factory: Optional[SessionFactory] = None,
    *,
    user_id: int,
    force: bool = False,
) -> SeedSummary:
    """Seed demo data idempotently for desktop workflows and return counts."""

    with _get_session(session_factory) as session:
        if not force:
            # Skip heavy re-seeding when data already present for this user.
            existing_tx = session.exec(
                select(Transaction.id).where(Transaction.user_id == user_id)
            ).first()
            if existing_tx is not None:
                return _build_seed_summary(session, user_id=user_id)

        categories = _seed_categories(session, user_id=user_id)
        accounts = _seed_accounts(session, user_id=user_id)
        _seed_transactions(session, categories, accounts, user_id=user_id)
        _seed_habits(session, user_id=user_id)
        _seed_liabilities(session, user_id=user_id)
        _seed_budget(session, categories, user_id=user_id)
        session.flush()
        return _build_seed_summary(session, user_id=user_id)


def _build_seed_summary(session: Session, *, user_id: int) -> SeedSummary:
    """Compile counts for tables populated by the demo seed."""

    tx_count = session.exec(
        select(func.count(Transaction.id)).where(Transaction.user_id == user_id)
    ).one()
    category_count = session.exec(
        select(func.count(Category.id)).where(Category.user_id == user_id)
    ).one()
    account_count = session.exec(
        select(func.count(Account.id)).where(Account.user_id == user_id)
    ).one()
    habit_count = session.exec(select(func.count(Habit.id)).where(Habit.user_id == user_id)).one()
    liability_count = session.exec(
        select(func.count(Liability.id)).where(Liability.user_id == user_id)
    ).one()
    budget_count = session.exec(
        select(func.count(Budget.id)).where(Budget.user_id == user_id)
    ).one()
    return SeedSummary(
        transactions=tx_count,
        categories=category_count,
        accounts=account_count,
        habits=habit_count,
        liabilities=liability_count,
        budgets=budget_count,
    )


EXPORT_RETENTION = 5


def _ensure_secure_directory(directory: Path) -> None:
    """Create the directory and set restrictive permissions when possible."""

    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except (NotImplementedError, PermissionError):  # pragma: no cover - platform specific
        pass


def _prune_old_exports(directory: Path, keep: int = EXPORT_RETENTION) -> None:
    """Remove export archives beyond the retention count."""

    archives = sorted(
        directory.glob("pocketsage_export_*.zip"),
        key=lambda file: file.stat().st_mtime,
        reverse=True,
    )
    for old in archives[keep:]:
        try:
            old.unlink()
        except OSError:  # pragma: no cover - best-effort cleanup
            pass


def run_export(
    output_dir: Path | None = None,
    session_factory: Optional[SessionFactory] = None,
    user_id: Optional[int] = None,
    retention: int = EXPORT_RETENTION,
) -> Path:
    """Generate export bundle for download and return path to zip file."""

    write_to_instance = output_dir is not None
    out_dir: Path | None = None
    if write_to_instance:
        out_dir = Path(output_dir) if not isinstance(output_dir, Path) else output_dir
        _ensure_secure_directory(out_dir)

    with TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        safe_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        csv_path = tmp / f"transactions-{safe_stamp}.csv"
        png_path = tmp / f"spending-{safe_stamp}.png"

        with _get_session(session_factory) as session:
            try:
                stmt = select(Transaction)
                if user_id is not None:
                    stmt = stmt.where(Transaction.user_id == user_id)
                txs = session.exec(stmt).all()
            except OperationalError:
                txs = []

            try:
                export_transactions_csv(transactions=txs, output_path=csv_path)
            except Exception:
                csv_path.write_text("id,occurred_at,amount,memo\n")

            try:
                export_spending_png(transactions=txs, output_path=png_path, renderer=None)  # type: ignore[arg-type]
            except Exception:
                png_path.write_bytes(b"")

        zip_name = f"pocketsage_export_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.zip"
        zip_path = (Path.cwd() / zip_name) if not out_dir else out_dir / zip_name

        with ZipFile(zip_path, "w") as archive:
            if csv_path.exists():
                archive.write(csv_path, arcname=csv_path.name)
            if png_path.exists():
                archive.write(png_path, arcname=png_path.name)

        if write_to_instance and out_dir is not None:
            _prune_old_exports(out_dir, keep=retention)

        return zip_path


def backup_database(
    output_dir: Path | None = None, config: Optional[BaseConfig] = None
) -> Path:
    """Copy the current database file (all users) to a backup location."""

    config = config or BaseConfig()
    db_path = config.DATA_DIR / config.DB_FILENAME
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    destination_root = output_dir if output_dir is not None else config.DATA_DIR / "backups"
    dest_dir = destination_root if isinstance(destination_root, Path) else Path(destination_root)
    _ensure_secure_directory(dest_dir)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    backup_path = dest_dir / f"pocketsage_backup_{stamp}.db"
    with db_path.open("rb") as src, backup_path.open("wb") as dst:
        dst.write(src.read())
    return backup_path


def restore_database(
    backup_file: Path, *, config: Optional[BaseConfig] = None, overwrite: bool = True
) -> Path:
    """Restore the database from a provided backup file."""

    config = config or BaseConfig()
    source = backup_file if isinstance(backup_file, Path) else Path(backup_file)
    if not source.exists():
        raise FileNotFoundError(f"Backup file not found: {source}")
    target = config.DATA_DIR / config.DB_FILENAME
    if not overwrite and target.exists():
        raise FileExistsError(f"Target database already exists at {target}")

    _ensure_secure_directory(config.DATA_DIR)
    with source.open("rb") as src, target.open("wb") as dst:
        dst.write(src.read())
    # Hint: caller should trigger app restart to reload connections.
    return target


__all__ = [
    "reset_demo_database",
    "run_demo_seed",
    "run_export",
    "EXPORT_RETENTION",
    "backup_database",
    "restore_database",
]

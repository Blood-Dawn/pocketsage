"""Admin utilities for the desktop app (demo seed, exports, retention)."""

from __future__ import annotations

import os
from calendar import monthrange
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Callable, Iterator, Optional
from zipfile import ZipFile

from sqlalchemy import func
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError
from sqlmodel import Session, SQLModel, select

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
    Liability,
    Transaction,
)
from .export_csv import export_transactions_csv
from .reports import export_spending_png

SessionFactory = Callable[[], Iterator[Session]]

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
        engine = getattr(bind, "engine", bind)
        return engine


def _seed_categories(session: Session) -> dict[str, Category]:
    categories_seed = [
        {
            "name": "Groceries",
            "slug": "groceries",
            "category_type": "expense",
            "color": "#4CAF50",
        },
        {
            "name": "Dining Out",
            "slug": "dining-out",
            "category_type": "expense",
            "color": "#FF7043",
        },
        {
            "name": "Utilities",
            "slug": "utilities",
            "category_type": "expense",
            "color": "#29B6F6",
        },
        {
            "name": "Transportation",
            "slug": "transportation",
            "category_type": "expense",
            "color": "#AB47BC",
        },
        {
            "name": "Wellness",
            "slug": "wellness",
            "category_type": "expense",
            "color": "#8D6E63",
        },
        {
            "name": "Coffee",
            "slug": "coffee",
            "category_type": "expense",
            "color": "#795548",
        },
        {
            "name": "Salary",
            "slug": "salary",
            "category_type": "income",
            "color": "#4CAF50",
        },
        {
            "name": "Paycheck",
            "slug": "paycheck",
            "category_type": "income",
            "color": "#2E7D32",
        },
        {
            "name": "Interest Income",
            "slug": "interest-income",
            "category_type": "income",
            "color": "#1B5E20",
        },
        {
            "name": "Transfer In",
            "slug": "transfer-in",
            "category_type": "income",
            "color": "#00796B",
        },
    ]
    categories: dict[str, Category] = {}
    for payload in categories_seed:
        existing = session.exec(select(Category).where(Category.slug == payload["slug"])).first()
        if existing:
            categories[payload["slug"]] = existing
            continue
        category = Category(**payload)
        session.add(category)
        session.flush()
        categories[payload["slug"]] = category
    session.flush()
    return categories


def _seed_accounts(session: Session) -> dict[str, Account]:
    accounts_seed = [
        {"name": "Everyday Checking", "currency": "USD"},
        {"name": "Rainy Day Savings", "currency": "USD"},
    ]
    accounts: dict[str, Account] = {}
    for payload in accounts_seed:
        existing = session.exec(select(Account).where(Account.name == payload["name"])).first()
        if existing:
            accounts[payload["name"]] = existing
            continue
        account = Account(**payload)
        session.add(account)
        session.flush()
        accounts[payload["name"]] = account
    session.flush()
    return accounts


def _seed_transactions(
    session: Session,
    categories: dict[str, Category],
    accounts: dict[str, Account],
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
            select(Transaction).where(Transaction.external_id == spec["external_id"])
        ).one_or_none()
        if existing is None:
            existing = Transaction(external_id=spec["external_id"])
            session.add(existing)
        existing.occurred_at = spec["occurred_at"]
        existing.amount = spec["amount"]
        existing.memo = spec["memo"]
        existing.category_id = categories[spec["category_slug"]].id
        existing.account_id = account.id
        existing.currency = account.currency


def _seed_habits(session: Session) -> None:
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
        existing = session.exec(select(Habit).where(Habit.name == spec["name"])).one_or_none()
        if existing is None:
            existing = Habit(
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

        entries = {
            entry.occurred_on: entry
            for entry in session.exec(
                select(HabitEntry).where(HabitEntry.habit_id == existing.id)
            ).all()
        }
        for occurred_on, value in spec["entries"]:
            entry = entries.get(occurred_on)
            if entry is None:
                session.add(
                    HabitEntry(
                        habit_id=existing.id,
                        occurred_on=occurred_on,
                        value=value,
                    )
                )
            else:
                entry.value = value


def _seed_liabilities(session: Session) -> None:
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
            select(Liability).where(Liability.name == spec["name"])
        ).one_or_none()
        if existing is None:
            session.add(Liability(**spec))
        else:
            existing.balance = spec["balance"]
            existing.apr = spec["apr"]
            existing.minimum_payment = spec["minimum_payment"]
            existing.due_day = spec["due_day"]


def _seed_budget(session: Session, categories: dict[str, Category]) -> None:
    now = datetime.now(timezone.utc)
    period_start = date(now.year, now.month, 1)
    period_end = date(now.year, now.month, monthrange(now.year, now.month)[1])
    existing_budget = session.exec(
        select(Budget).where(Budget.period_start == period_start, Budget.period_end == period_end)
    ).one_or_none()
    if existing_budget is None:
        budget = Budget(
            period_start=period_start,
            period_end=period_end,
            label=f"{now.strftime('%B %Y')} Demo Budget",
        )
        session.add(budget)
        session.flush()
        existing_budget = budget

    coffee_category = categories.get("coffee")
    if coffee_category:
        existing_line = session.exec(
            select(BudgetLine).where(
                BudgetLine.budget_id == existing_budget.id,
                BudgetLine.category_id == coffee_category.id,
            )
        ).one_or_none()
        if existing_line is None:
            session.add(
                BudgetLine(
                    budget_id=existing_budget.id,
                    category_id=coffee_category.id,
                    planned_amount=50.0,
                    rollover_enabled=False,
                )
            )


def reset_demo_database(session_factory: Optional[SessionFactory] = None) -> SeedSummary:
    """Drop the schema and reseed demo data for desktop demos."""

    engine = _resolve_engine(session_factory)
    SQLModel.metadata.drop_all(engine)
    init_database(engine)
    return run_demo_seed(session_factory=session_factory, force=True)


def run_demo_seed(
    session_factory: Optional[SessionFactory] = None,
    *,
    force: bool = False,
) -> SeedSummary:
    """Seed demo data idempotently for desktop workflows and return counts."""

    with _get_session(session_factory) as session:
        if not force:
            # Skip heavy re-seeding when data already present.
            existing_tx = session.exec(select(Transaction.id)).first()
            if existing_tx is not None:
                return _build_seed_summary(session)

        categories = _seed_categories(session)
        accounts = _seed_accounts(session)
        _seed_transactions(session, categories, accounts)
        _seed_habits(session)
        _seed_liabilities(session)
        _seed_budget(session, categories)
        session.flush()
        return _build_seed_summary(session)


def _build_seed_summary(session: Session) -> SeedSummary:
    """Compile counts for tables populated by the demo seed."""

    tx_count = session.exec(select(func.count(Transaction.id))).one()
    category_count = session.exec(select(func.count(Category.id))).one()
    account_count = session.exec(select(func.count(Account.id))).one()
    habit_count = session.exec(select(func.count(Habit.id))).one()
    liability_count = session.exec(select(func.count(Liability.id))).one()
    budget_count = session.exec(select(func.count(Budget.id))).one()
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
                txs = session.exec(select(Transaction)).all()
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
            _prune_old_exports(out_dir)

        return zip_path


__all__ = [
    "reset_demo_database",
    "run_demo_seed",
    "run_export",
    "EXPORT_RETENTION",
]

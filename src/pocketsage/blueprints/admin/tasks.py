"""Admin asynchronous task stubs."""

from __future__ import annotations

import os
from calendar import monthrange
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from sqlalchemy.exc import OperationalError
from sqlmodel import select

from pocketsage.extensions import session_scope
from pocketsage.models import Account, Budget, BudgetLine, Category, Transaction
from pocketsage.services.export_csv import export_transactions_csv
from pocketsage.services.reports import export_spending_png


def run_demo_seed() -> None:
    """Seed demo data for PocketSage.

    Populate a demo investment account with holdings, paired transactions, and
    a CSV mapping hint the first time the database is initialized.
    """

    with session_scope() as session:
        # Idempotency: if any transactions already exist, skip seeding.
        existing_tx = session.exec(select(Transaction.id)).first()
        if existing_tx is not None:
            return

        # Seed canonical categories covering common inflows and outflows.
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
            {"name": "Paycheck", "slug": "paycheck", "category_type": "income", "color": "#2E7D32"},
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
            {"name": "Coffee", "slug": "coffee", "category_type": "expense", "color": "#795548"},
            {"name": "Salary", "slug": "salary", "category_type": "income", "color": "#4CAF50"},
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

        # Use timezone-aware UTC datetimes for persisted rows.
        now = datetime.now(timezone.utc)
        two_tx_seed = [
            {
                "amount": 1500.00,
                "memo": "Salary",
                "category": "salary",
                "account": "Everyday Checking",
            },
            {
                "amount": -4.50,
                "memo": "Coffee",
                "category": "coffee",
                "account": "Everyday Checking",
            },
        ]

        for seed in two_tx_seed:
            transaction = Transaction(
                occurred_at=now,
                amount=seed["amount"],
                memo=seed["memo"],
                category_id=categories[seed["category"]].id,
                account_id=accounts[seed["account"]].id,
                currency="USD",
            )
            session.add(transaction)

        # Minimal budget scaffold for current month to keep downstream queries safe.
        period_start = date(now.year, now.month, 1)
        period_end = date(now.year, now.month, monthrange(now.year, now.month)[1])
        budget = Budget(
            period_start=period_start,
            period_end=period_end,
            label=f"{now.strftime('%B %Y')} Demo Budget",
        )
        session.add(budget)
        session.flush()
        session.add(
            BudgetLine(
                budget_id=budget.id,
                category_id=categories["coffee"].id,
                planned_amount=50.0,
                rollover_enabled=False,
            )
        )


EXPORT_RETENTION = 5


def _ensure_secure_directory(directory: Path) -> None:
    """Create the directory and set restrictive permissions when possible."""

    directory.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(directory, 0o700)
    except (NotImplementedError, PermissionError):  # pragma: no cover - platform specific
        # Best effort: Windows and some filesystems may not support chmod.
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


def run_export(output_dir: Path | None = None) -> Path:
    """Generate export bundle for download and return path to zip file.

    If ``output_dir`` is provided, the resulting zip will be written there;
    otherwise a temporary directory is used and the zip is created in the current
    working directory.
    """

    write_to_instance = output_dir is not None
    out_dir: Path | None = None
    if write_to_instance:
        out_dir = (
            Path(output_dir)
            if output_dir is not None and not isinstance(output_dir, Path)
            else output_dir
        )
        if out_dir is not None and not isinstance(out_dir, Path):
            out_dir = Path(out_dir)
        if out_dir is not None:
            _ensure_secure_directory(out_dir)

    with TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        safe_stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        csv_path = tmp / f"transactions-{safe_stamp}.csv"
        png_path = tmp / f"spending-{safe_stamp}.png"

        # Export transactions
        with session_scope() as session:
            try:
                txs = session.exec(select(Transaction)).all()  # list of Transaction
            except OperationalError:
                txs = []  # Schema drift fallback: proceed with empty dataset.

            # Best-effort: call stubs that may raise; catch and continue.
            try:
                export_transactions_csv(transactions=txs, output_path=csv_path)
            except Exception:
                csv_path.write_text("id,occurred_at,amount,memo\n")

            try:
                export_spending_png(transactions=txs, output_path=png_path, renderer=None)  # type: ignore[arg-type]
            except Exception:
                png_path.write_bytes(b"")

        zip_name = f"pocketsage_export_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}.zip"
        if write_to_instance and out_dir is not None:
            # Ensure out_dir is a Path object
            out_dir_path = Path(out_dir) if not isinstance(out_dir, Path) else out_dir
            zip_path = out_dir_path / zip_name
        else:
            zip_path = Path.cwd() / zip_name

        with ZipFile(zip_path, "w") as z:
            if csv_path.exists():
                z.write(csv_path, arcname=csv_path.name)
            if png_path.exists():
                z.write(png_path, arcname=png_path.name)

        if write_to_instance and out_dir is not None:
            _prune_old_exports(out_dir)

        return zip_path

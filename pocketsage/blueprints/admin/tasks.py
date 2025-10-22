"""Admin asynchronous task stubs."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from sqlalchemy.exc import OperationalError
from sqlmodel import select

from pocketsage.extensions import session_scope
from pocketsage.models import AppSetting, Account, Holding, Transaction
from pocketsage.blueprints.portfolio.repository import SqlModelPortfolioRepository
from pocketsage.services.export_csv import export_transactions_csv
from pocketsage.services.reports import export_spending_png


def run_demo_seed() -> None:
    """Seed demo data for PocketSage.

    Populate a demo investment account with holdings, paired transactions, and
    a CSV mapping hint the first time the database is initialized.
    """

    with session_scope() as session:
        # Bail early if demo portfolio data already exists.
        existing_holding = session.exec(select(Holding.id).limit(1)).first()
        if existing_holding is not None:
            return

        repo = SqlModelPortfolioRepository(session)

        account = session.exec(
            select(Account).where(Account.name == "Demo Investment Portfolio")
        ).one_or_none()
        if account is None:
            account = Account(name="Demo Investment Portfolio", currency="USD")
            session.add(account)
            session.flush()

        holdings_payload = [
            {
                "symbol": "AAPL",
                "quantity": 12.0,
                "avg_price": 148.25,
                "currency": "USD",
                "acquired_at": datetime(2022, 3, 14, 15, 9, tzinfo=timezone.utc),
            },
            {
                "symbol": "VOO",
                "quantity": 8.5,
                "avg_price": 396.4,
                "currency": "USD",
                "acquired_at": datetime(2021, 9, 7, 12, 30, tzinfo=timezone.utc),
            },
            {
                "symbol": "SHOP",
                "quantity": 5.0,
                "avg_price": 1420.15,
                "currency": "CAD",
                "acquired_at": datetime(2023, 1, 11, 10, 0, tzinfo=timezone.utc),
            },
        ]

        for entry in holdings_payload:
            holding = Holding(
                symbol=entry["symbol"],
                quantity=entry["quantity"],
                avg_price=entry["avg_price"],
                acquired_at=entry["acquired_at"],
                account_id=account.id,
                currency=entry["currency"],
            )
            session.add(holding)

            external_id = repo._build_external_id(
                symbol=entry["symbol"],
                account_id=account.id,
                currency=entry["currency"],
            )

            transaction = session.exec(
                select(Transaction).where(Transaction.external_id == external_id)
            ).one_or_none()
            if transaction is None:
                transaction = Transaction(external_id=external_id)

            transaction.occurred_at = entry["acquired_at"]
            transaction.amount = entry["quantity"] * entry["avg_price"]
            transaction.memo = f"Seeded portfolio position for {entry['symbol']}"
            transaction.account_id = account.id
            transaction.currency = entry["currency"]

            session.add(transaction)

        mapping_key = "demo.portfolio.csv_mapping"
        mapping_value = (
            "symbol:Ticker,quantity:Shares,avg_price:PurchasePrice,acquired_at:PurchaseDate"
        )
        app_setting = session.get(AppSetting, mapping_key)
        if app_setting is None:
            app_setting = AppSetting(
                key=mapping_key,
                value=mapping_value,
                description="Sample CSV column mapping showcased in demo seeds.",
            )
        else:
            app_setting.value = mapping_value
            app_setting.description = "Sample CSV column mapping showcased in demo seeds."

        session.add(app_setting)


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

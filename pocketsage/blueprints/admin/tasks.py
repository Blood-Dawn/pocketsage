"""Admin asynchronous task stubs."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from sqlalchemy.exc import OperationalError
from sqlmodel import select

from pocketsage.extensions import session_scope
from pocketsage.models import Habit, HabitEntry, Liability, Transaction
from pocketsage.services.export_csv import export_transactions_csv
from pocketsage.services.reports import export_spending_png


def run_demo_seed() -> None:
    """Seed demo data for PocketSage.

    This is intentionally minimal and safe: it inserts a couple of demo
    transactions only if the DB is empty.
    """

    with session_scope() as session:
        now = datetime.now(timezone.utc)

        # Avoid heavy dependencies; insert a couple of transactions if none exist.
        transactions_present = session.exec(select(Transaction)).first() is not None
        if not transactions_present:
            t1 = Transaction(occurred_at=now, amount=-12.34, memo="Coffee")
            t2 = Transaction(occurred_at=now, amount=1500.0, memo="Salary")
            session.add(t1)
            session.add(t2)

        # Seed demo habits with a rolling two-week streak snapshot to highlight
        # variance in completion for presenters.
        habits_present = session.exec(select(Habit)).first() is not None
        if not habits_present:
            today = now.date()
            two_week_history = 14
            habits_payload = [
                {
                    "habit": Habit(
                        name="Morning Walk",
                        description="Get outside for 20 minutes before work.",
                        cadence="daily",
                    ),
                    # Oldest -> newest; 11/14 completions for presenters to call out.
                    "history": [1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 0, 1, 1],
                },
                {
                    "habit": Habit(
                        name="Evening Journal",
                        description="Reflect on the day with three bullet points.",
                        cadence="daily",
                    ),
                    # Alternating successes: 7/14 completions to show comeback potential.
                    "history": [1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0, 1, 0],
                },
                {
                    "habit": Habit(
                        name="Sunday Meal Prep",
                        description="Batch cook lunches for the upcoming week.",
                        cadence="weekly",
                    ),
                    # Weekly cadence snapshot across two Sundays.
                    "history": [1, 0],
                    "weekly_offsets": [7, 0],
                },
            ]

            for payload in habits_payload:
                habit = payload["habit"]
                session.add(habit)
                session.flush()  # ensure habit.id populated for entries

                history = payload.get("history", [])
                if "weekly_offsets" in payload:
                    offsets = payload["weekly_offsets"]
                else:
                    offsets = [two_week_history - 1 - idx for idx in range(len(history))]

                for value, offset in zip(history, offsets):
                    occurred_on = today - timedelta(days=offset)

                    entry = HabitEntry(
                        habit_id=habit.id,
                        occurred_on=occurred_on,
                        value=value,
                    )
                    session.add(entry)

        # Seed liabilities to provide payoff comparison talking points.
        liabilities_present = session.exec(select(Liability)).first() is not None
        if not liabilities_present:
            liabilities = [
                Liability(
                    name="Redwood Rewards Card",
                    balance=5200.45,
                    apr=19.99,
                    minimum_payment=165.0,
                    due_day=15,
                    payoff_strategy="avalanche",
                ),
                Liability(
                    name="State University Loan",
                    balance=18250.0,
                    apr=5.45,
                    minimum_payment=205.72,
                    due_day=5,
                    payoff_strategy="snowball",
                ),
                Liability(
                    name="Canyon Auto Loan",
                    balance=11400.0,
                    apr=6.9,
                    minimum_payment=340.0,
                    due_day=22,
                    payoff_strategy="snowball",
                ),
            ]

            for liability in liabilities:
                session.add(liability)


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

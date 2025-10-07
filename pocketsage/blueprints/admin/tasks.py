"""Admin asynchronous task stubs."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from sqlmodel import select

from pocketsage.extensions import session_scope
from pocketsage.models import Transaction
from pocketsage.services.export_csv import export_transactions_csv
from pocketsage.services.reports import export_spending_png


def run_demo_seed() -> None:
    """Seed demo data for PocketSage."""

    # Minimal, safe demo seed that inserts a small set of transactions.
    with session_scope() as session:
        # Avoid heavy dependencies; insert a couple of transactions if none exist.
        count = len(list(session.exec(select(Transaction))))
        if count > 0:
            return
        from datetime import datetime as _dt

        t1 = Transaction(occurred_at=_dt.utcnow(), amount=-12.34, memo="Coffee")
        t2 = Transaction(occurred_at=_dt.utcnow(), amount=1500.0, memo="Salary")
        session.add(t1)
        session.add(t2)


def run_export() -> Path:
    """Generate export bundle for download and return path to zip file."""

    with TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        csv_path = tmp / f"transactions-{datetime.utcnow().isoformat()}.csv"
        png_path = tmp / f"spending-{datetime.utcnow().isoformat()}.png"

        # Export transactions
        with session_scope() as session:
            txs = list(session.exec(select(Transaction)).all())
            # Best-effort: call stubs that may raise NotImplementedError; catch and continue.
            try:
                export_transactions_csv(transactions=txs, output_path=csv_path)
            except Exception:
                # create an empty placeholder
                csv_path.write_text("id,occurred_at,amount,memo\n")

            try:
                export_spending_png(transactions=txs, output_path=png_path, renderer=None)  # type: ignore[arg-type]
            except Exception:
                png_path.write_bytes(b"")

        zip_path = (
            Path.cwd() / f"pocketsage_export_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}.zip"
        )
        with ZipFile(zip_path, "w") as z:
            if csv_path.exists():
                z.write(csv_path, arcname=csv_path.name)
            if png_path.exists():
                z.write(png_path, arcname=png_path.name)

        return zip_path

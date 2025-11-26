from __future__ import annotations

import os
import tempfile
from pathlib import Path

from pocketsage.desktop.context import create_app_context
from pocketsage.services import importers


def _new_ctx():
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "app.db"
    os.environ["POCKETSAGE_DATA_DIR"] = tmp_dir
    os.environ["POCKETSAGE_DATABASE_URL"] = f"sqlite:///{db_path}"
    ctx = create_app_context()
    ctx._tmp_dir = tmp_dir  # keep reference alive for test duration
    return ctx


def test_import_ledger_transactions_creates_data():
    ctx = _new_ctx()
    csv_path = Path(ctx.config.DATA_DIR) / "ledger.csv"
    csv_path.write_text(
        "date,amount,memo,category,account,currency,transaction_id\n"
        "2025-01-01,1000,Paycheck,Salary,Checking,USD,txn-1\n"
        "2025-01-02,-50,Grocery store,Groceries,Checking,USD,txn-2\n",
        encoding="utf-8",
    )

    created = importers.import_ledger_transactions(
        csv_path=csv_path,
        session_factory=ctx.session_factory,
        user_id=ctx.require_user_id(),
    )

    assert created == 2
    txns = ctx.transaction_repo.search(
        start_date=None, end_date=None, category_id=None, text=None, user_id=ctx.require_user_id()
    )
    assert len(txns) == 2
    # Accounts and categories auto-created
    assert ctx.account_repo.list_all(user_id=ctx.require_user_id())
    assert ctx.category_repo.list_all(user_id=ctx.require_user_id())


def test_import_portfolio_holdings_creates_data_and_market_value():
    ctx = _new_ctx()
    csv_path = Path(ctx.config.DATA_DIR) / "portfolio.csv"
    csv_path.write_text(
        "symbol,shares,price,market_price,account,currency\n"
        "AAPL,2,100,110,Brokerage,USD\n"
        "MSFT,1,300,320,Brokerage,USD\n",
        encoding="utf-8",
    )

    created = importers.import_portfolio_holdings(
        csv_path=csv_path,
        session_factory=ctx.session_factory,
        user_id=ctx.require_user_id(),
    )

    assert created == 2
    holdings = ctx.holding_repo.list_all(user_id=ctx.require_user_id())
    assert len(holdings) == 2
    mv = ctx.holding_repo.get_total_market_value(user_id=ctx.require_user_id())
    assert mv > 0

from __future__ import annotations

import os
from calendar import monthrange
from datetime import datetime
from types import SimpleNamespace
from typing import Callable

import flet as ft
import pytest

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import admin, budgets, debts, habits, ledger, portfolio
from pocketsage.desktop.views.dashboard import build_dashboard_view as create_dashboard_view
from pocketsage.models import Account, Budget, Category, Liability, Transaction


class DummyPage:
    """Minimal stand-in for flet.Page used to drive button handlers."""

    def __init__(self):
        self.views: list[ft.View] = []
        self.route: str = ""
        self.snack_bar = None
        self.dialog = None
        self.overlay: list[ft.Control] = []
        self.padding = 0
        self.window_width = 1280
        self.window_height = 800
        self.window_min_width = 1024
        self.window_min_height = 600
        self.theme_mode = ft.ThemeMode.DARK

    def go(self, route: str):
        self.route = route

    def update(self):
        return None


def _init_ctx(monkeypatch: pytest.MonkeyPatch, tmp_path) -> tuple:
    data_dir = tmp_path / "instance"
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    ctx = create_app_context()
    page = DummyPage()
    return ctx, page


def _find_control(root: ft.Control, predicate: Callable[[ft.Control], bool]) -> ft.Control | None:
    """Depth-first search of controls."""

    if predicate(root):
        return root
    for attr in ("controls", "content", "actions", "rows", "cells"):
        children = getattr(root, attr, None)
        if children is None:
            continue
        if isinstance(children, list):
            for child in children:
                found = _find_control(child, predicate)
                if found:
                    return found
        elif isinstance(children, ft.Control):
            found = _find_control(children, predicate)
            if found:
                return found
    return None


def _click(control: ft.Control):
    assert hasattr(control, "on_click") and callable(control.on_click)
    control.on_click(SimpleNamespace())


def test_ledger_add_transaction_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    category = ctx.category_repo.create(
        Category(name="Groceries", slug="groceries", category_type="expense", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )
    account = ctx.account_repo.create(
        Account(name="Checking", currency="USD", user_id=ctx.require_user_id()), user_id=ctx.require_user_id()
    )

    view = ledger.build_ledger_view(ctx, page)
    add_btn = _find_control(
        view,
        lambda c: isinstance(c, ft.FilledButton)
        and "Add transaction" in getattr(c, "text", ""),
    )
    assert add_btn is not None

    _click(add_btn)
    dialog = page.dialog
    amount_field = _find_control(dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Amount")
    memo_field = _find_control(
        dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Description"
    )
    date_field = _find_control(dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Date")
    category_dd = _find_control(dialog, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Category")
    account_dd = _find_control(dialog, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Account")
    amount_field.value = "25.50"
    memo_field.value = "Test purchase"
    date_field.value = "2025-01-02"
    category_dd.value = str(category.id)
    account_dd.value = str(account.id)
    save_btn = dialog.actions[1]
    _click(save_btn)

    txns = ctx.transaction_repo.search(
        start_date=None, end_date=None, category_id=None, text=None, user_id=ctx.require_user_id()
    )
    assert any(t.memo == "Test purchase" for t in txns)


def test_ledger_edit_transaction_button_updates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    cat = ctx.category_repo.create(
        Category(name="General", slug="general", category_type="expense", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )
    acct = ctx.account_repo.create(
        Account(name="Checking", currency="USD", user_id=ctx.require_user_id()), user_id=ctx.require_user_id()
    )
    existing = ctx.transaction_repo.create(
        Transaction(
            amount=-10.0,
            memo="Old",
            occurred_at=datetime(2025, 1, 1),
            category_id=cat.id,
            account_id=acct.id,
            user_id=ctx.require_user_id(),
        ),
        user_id=ctx.require_user_id(),
    )

    view = ledger.build_ledger_view(ctx, page)
    table = _find_control(view, lambda c: isinstance(c, ft.DataTable))
    edit_btn = _find_control(
        table, lambda c: isinstance(c, ft.IconButton) and getattr(c, "tooltip", "") == "Edit"
    )
    assert edit_btn is not None
    _click(edit_btn)
    dialog = page.dialog
    memo_field = _find_control(
        dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Description"
    )
    memo_field.value = "Updated"
    save_btn = dialog.actions[1]
    _click(save_btn)

    refreshed = ctx.transaction_repo.get_by_id(existing.id, user_id=ctx.require_user_id())
    assert refreshed.memo == "Updated"


def test_ledger_delete_transaction_button_removes_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    cat = ctx.category_repo.create(
        Category(name="General", slug="general", category_type="expense", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )
    acct = ctx.account_repo.create(
        Account(name="Checking", currency="USD", user_id=ctx.require_user_id()), user_id=ctx.require_user_id()
    )
    txn = ctx.transaction_repo.create(
        Transaction(
            amount=-5.0,
            memo="Delete me",
            occurred_at=datetime(2025, 1, 1),
            category_id=cat.id,
            account_id=acct.id,
            user_id=ctx.require_user_id(),
        ),
        user_id=ctx.require_user_id(),
    )

    view = ledger.build_ledger_view(ctx, page)
    table = _find_control(view, lambda c: isinstance(c, ft.DataTable))
    delete_btn = _find_control(
        table, lambda c: isinstance(c, ft.IconButton) and getattr(c, "tooltip", "") == "Delete"
    )
    assert delete_btn is not None
    _click(delete_btn)
    # confirm dialog
    confirm_dialog = page.dialog
    confirm_btn = next(a for a in confirm_dialog.actions if getattr(a, "text", "") == "Confirm")
    _click(confirm_btn)

    assert ctx.transaction_repo.get_by_id(txn.id, user_id=ctx.require_user_id()) is None


def test_habits_add_button_creates_habit(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    view = habits.build_habits_view(ctx, page)
    add_btn = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add habit"
    )
    assert add_btn is not None
    _click(add_btn)
    dialog = page.dialog
    name_field = dialog.content.controls[0]
    name_field.value = "Meditate"
    save_btn = dialog.actions[1]
    _click(save_btn)
    assert any(h.name == "Meditate" for h in ctx.habit_repo.list_active(user_id=ctx.require_user_id()))


def test_liabilities_add_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    view = debts.build_debts_view(ctx, page)
    add_btn = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add liability"
    )
    assert add_btn is not None
    _click(add_btn)
    dialog = page.dialog
    name, balance, apr, minimum_payment, due_day = dialog.content.controls
    name.value = "Card"
    balance.value = "1000"
    apr.value = "10"
    minimum_payment.value = "50"
    due_day.value = "12"
    save_btn = dialog.actions[1]
    _click(save_btn)
    assert any(li.name == "Card" for li in ctx.liability_repo.list_all(user_id=ctx.require_user_id()))


def test_portfolio_add_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    account = ctx.account_repo.create(
        Account(name="Brokerage", currency="USD", user_id=ctx.require_user_id()), user_id=ctx.require_user_id()
    )
    view = portfolio.build_portfolio_view(ctx, page)
    add_btn = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add holding"
    )
    assert add_btn is not None
    _click(add_btn)
    dialog = page.dialog
    symbol = _find_control(dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Symbol")
    qty = _find_control(dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Quantity")
    price = _find_control(dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Average price")
    market_price = _find_control(
        dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Market price (optional)"
    )
    account_dd = _find_control(dialog, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Account")
    symbol.value = "AAPL"
    qty.value = "2"
    price.value = "100"
    market_price.value = "110"
    account_dd.value = str(account.id)
    save_btn = dialog.actions[1]
    _click(save_btn)
    assert any(h.symbol == "AAPL" for h in ctx.holding_repo.list_all(user_id=ctx.require_user_id()))


def test_budget_add_line_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    start = ctx.current_month
    end = start.replace(day=monthrange(start.year, start.month)[1])
    budget = ctx.budget_repo.create(
        Budget(period_start=start, period_end=end, label="Test budget", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )
    category = ctx.category_repo.create(
        Category(name="Dining", slug="dining", category_type="expense", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )

    view = budgets.build_budgets_view(ctx, page)
    add_btn = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add line"
    )
    assert add_btn is not None
    _click(add_btn)
    dialog = page.dialog
    category_dd, amount_field = dialog.content.controls
    category_dd.value = str(category.id)
    amount_field.value = "250"
    save_btn = dialog.actions[1]
    _click(save_btn)
    lines = ctx.budget_repo.get_lines_for_budget(budget.id, user_id=ctx.require_user_id())
    assert any(line.planned_amount == 250 for line in lines)


def test_admin_seed_button_invokes_seed(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    ctx.admin_mode = True
    monkeypatch.setattr(ft.Text, "update", lambda self: None)

    calls = {"seed": False}

    def fake_seed(**kwargs):
        calls["seed"] = True
        return SimpleNamespace(transactions=1, categories=1, accounts=1, habits=1, liabilities=1, budgets=1)

    monkeypatch.setattr(admin, "run_heavy_seed", fake_seed)
    monkeypatch.setattr(admin, "run_demo_seed", fake_seed)
    view = admin.build_admin_view(ctx, page)
    seed_btn = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Run Demo Seed"
    )
    assert seed_btn is not None
    _click(seed_btn)
    assert calls["seed"] is True


def test_admin_reset_button_invokes_reset(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    ctx.admin_mode = True
    monkeypatch.setattr(ft.Text, "update", lambda self: None)
    calls = {"reset": False}

    def fake_reset(**kwargs):
        calls["reset"] = True
        return SimpleNamespace(transactions=0, categories=0, accounts=0, habits=0, liabilities=0, budgets=0)

    monkeypatch.setattr(admin, "reset_demo_database", fake_reset)
    view = admin.build_admin_view(ctx, page)
    reset_btn = _find_control(
        view, lambda c: isinstance(c, ft.TextButton) and getattr(c, "text", "") == "Reset Demo Data"
    )
    assert reset_btn is not None
    _click(reset_btn)
    assert calls["reset"] is True


def test_dashboard_quick_add_opens_ledger_dialog(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page = _init_ctx(monkeypatch, tmp_path)
    dash_view = create_dashboard_view(ctx, page)
    add_btn = _find_control(
        dash_view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add Transaction"
    )
    assert add_btn is not None
    _click(add_btn)
    # Navigate to ledger and ensure dialog opens automatically
    ledger_view = ledger.build_ledger_view(ctx, page)
    assert page.dialog is not None

from __future__ import annotations

import os
from calendar import monthrange
from typing import Callable

import flet as ft
import pytest

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import budgets, debts, habits, ledger, portfolio
from pocketsage.models import Account, Budget, Category
from pocketsage.services import auth


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
    user = auth.create_user(
        username="buttons-admin",
        password="password",
        role="admin",
        session_factory=ctx.session_factory,
    )
    ctx.current_user = user
    page = DummyPage()
    return ctx, page, user


def _find_control(root: ft.Control, predicate: Callable[[ft.Control], bool]) -> ft.Control | None:
    """Depth-first search of controls."""

    if predicate(root):
        return root
    for attr in ("controls", "content", "actions"):
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
    """Invoke an on_click handler if present."""

    assert hasattr(control, "on_click") and callable(control.on_click)
    control.on_click(type("Evt", (), {})())


def _find_text_field(root: ft.Control, label: str) -> ft.TextField:
    control = _find_control(
        root,
        lambda c: isinstance(c, ft.TextField) and getattr(c, "label", None) == label,
    )
    assert control is not None
    return control  # type: ignore[return-value]


def test_add_transaction_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page, user = _init_ctx(monkeypatch, tmp_path)
    category = ctx.category_repo.create(
        Category(name="Groceries", slug="groceries", category_type="expense", user_id=user.id),
        user_id=user.id,
    )
    account = ctx.account_repo.create(
        Account(name="Checking", currency="USD", user_id=user.id), user_id=user.id
    )

    view = ledger.build_ledger_view(ctx, page)
    add_btn = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add transaction"
    )
    assert add_btn is not None

    _click(add_btn)
    dialog = page.dialog
    amount_field = _find_text_field(dialog, "Amount")
    memo_field = _find_text_field(dialog, "Memo")
    date_field = _find_text_field(dialog, "Date")
    category_dd = _find_control(dialog, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Category")
    account_dd = _find_control(dialog, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Account")
    amount_field.value = "25.50"
    memo_field.value = "Test purchase"
    category_dd.value = str(category.id)
    account_dd.value = str(account.id)
    save_btn = dialog.actions[1]
    _click(save_btn)

    txns = ctx.transaction_repo.search(
        start_date=None, end_date=None, category_id=None, text=None, user_id=user.id
    )
    assert any(t.memo == "Test purchase" for t in txns)


def test_add_liability_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page, user = _init_ctx(monkeypatch, tmp_path)
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

    liabilities = ctx.liability_repo.list_all(user_id=user.id)
    assert any(li.name == "Card" for li in liabilities)


def test_add_habit_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page, user = _init_ctx(monkeypatch, tmp_path)
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

    habits_created = ctx.habit_repo.list_active(user_id=user.id)
    assert any(h.name == "Meditate" for h in habits_created)


def test_add_holding_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page, user = _init_ctx(monkeypatch, tmp_path)
    account = ctx.account_repo.create(
        Account(name="Brokerage", currency="USD", user_id=user.id), user_id=user.id
    )
    view = portfolio.build_portfolio_view(ctx, page)
    add_btn = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add holding"
    )
    assert add_btn is not None

    _click(add_btn)
    dialog = page.dialog
    symbol = _find_text_field(dialog, "Symbol")
    qty = _find_text_field(dialog, "Quantity")
    price = _find_text_field(dialog, "Average price")
    market_price = _find_text_field(dialog, "Market price (optional)")
    account_dd = _find_control(
        dialog, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Account"
    )
    symbol.value = "AAPL"
    qty.value = "2"
    price.value = "100"
    market_price.value = "110"
    account_dd.value = str(account.id)
    save_btn = dialog.actions[1]
    _click(save_btn)

    holdings = ctx.holding_repo.list_all(user_id=user.id)
    assert any(h.symbol == "AAPL" for h in holdings)


def test_add_budget_line_button_creates_record(monkeypatch: pytest.MonkeyPatch, tmp_path):
    ctx, page, user = _init_ctx(monkeypatch, tmp_path)
    start = ctx.current_month
    end = start.replace(day=monthrange(start.year, start.month)[1])
    budget = ctx.budget_repo.create(
        Budget(period_start=start, period_end=end, label="Test budget", user_id=user.id),
        user_id=user.id,
    )
    category = ctx.category_repo.create(
        Category(name="Dining", slug="dining", category_type="expense", user_id=user.id),
        user_id=user.id,
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

    lines = ctx.budget_repo.get_lines_for_budget(budget.id, user_id=user.id)
    assert any(line.planned_amount == 250 for line in lines)

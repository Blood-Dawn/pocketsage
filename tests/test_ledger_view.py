from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Callable

import flet as ft
import pytest
from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import ledger
from pocketsage.models import Account, Category, Transaction


class _PageStub:
    def __init__(self):
        self.overlay: list[ft.Control] = []
        self.snack_bar = None
        self.dialog = None
        self.route = "/"
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


def _ctx_and_page(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    data_dir = tmp_path / "instance"
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    ctx = create_app_context()
    page = _PageStub()
    return ctx, page


def _find_control(root: ft.Control, predicate: Callable[[ft.Control], bool]) -> ft.Control | None:
    """Depth-first search for a control matching predicate."""

    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        if id(control) in seen:
            continue
        seen.add(id(control))
        try:
            if predicate(control):
                return control
        except Exception:
            pass
        for attr in ("controls", "content", "actions", "leading", "trailing", "title", "subtitle"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return None


def _summary_values(root: ft.Control) -> list[str]:
    texts: list[str] = []
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        if id(control) in seen:
            continue
        seen.add(id(control))
        if isinstance(control, ft.Text) and getattr(control, "weight", None) == ft.FontWeight.BOLD:
            if isinstance(getattr(control, "size", None), (int, float)) and control.size >= 20:
                texts.append(control.value or "")
        for attr in ("controls", "content", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return texts


def test_all_categories_option_loads_transactions(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    ctx, page = _ctx_and_page(monkeypatch, tmp_path)
    cat_income = ctx.category_repo.create(
        Category(
            name="Salary",
            slug="salary",
            category_type="income",
            user_id=ctx.require_user_id(),
        ),
        user_id=ctx.require_user_id(),
    )
    cat_expense = ctx.category_repo.create(
        Category(
            name="Food",
            slug="food",
            category_type="expense",
            user_id=ctx.require_user_id(),
        ),
        user_id=ctx.require_user_id(),
    )
    acct = ctx.account_repo.create(
        Account(name="Checking", currency="USD", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )
    ctx.transaction_repo.create(
        Transaction(
            amount=500.0,
            memo="Paycheck",
            occurred_at=date.today(),
            category_id=cat_income.id,
            account_id=acct.id,
            user_id=ctx.require_user_id(),
        ),
        user_id=ctx.require_user_id(),
    )
    ctx.transaction_repo.create(
        Transaction(
            amount=-30.0,
            memo="Lunch",
            occurred_at=date.today(),
            category_id=cat_expense.id,
            account_id=acct.id,
            user_id=ctx.require_user_id(),
        ),
        user_id=ctx.require_user_id(),
    )

    view = ledger.build_ledger_view(ctx, page)
    category_dd = _find_control(
        view, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Category"
    )
    apply_btn = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Apply"
    )
    table = _find_control(view, lambda c: isinstance(c, ft.DataTable))

    assert category_dd is not None and apply_btn is not None and table is not None
    category_dd.value = "all"
    apply_btn.on_click(None)

    assert len(table.rows) >= 2


def test_summary_updates_after_add(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    ctx, page = _ctx_and_page(monkeypatch, tmp_path)
    income_cat = ctx.category_repo.create(
        Category(name="Bonus", slug="bonus", category_type="income", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )
    account = ctx.account_repo.create(
        Account(name="Checking", currency="USD", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )

    view = ledger.build_ledger_view(ctx, page)
    add_btn = _find_control(
        view,
        lambda c: isinstance(c, ft.FilledButton)
        and "Add transaction" in getattr(c, "text", ""),
    )
    assert add_btn is not None
    add_btn.on_click(None)
    dialog = page.dialog
    assert dialog is not None

    amount_field = _find_control(
        dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Amount"
    )
    description_field = _find_control(
        dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Description"
    )
    date_field = _find_control(
        dialog, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Date"
    )
    type_group = _find_control(dialog, lambda c: isinstance(c, ft.RadioGroup))
    category_dd = _find_control(
        dialog, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Category"
    )
    account_dd = _find_control(
        dialog, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Account"
    )
    assert all([amount_field, description_field, date_field, type_group, category_dd, account_dd])

    type_group.value = "income"
    if type_group.on_change:
        type_group.on_change(None)
    amount_field.value = "120.00"
    description_field.value = "Year-end bonus"
    date_field.value = date.today().isoformat()
    category_dd.value = str(income_cat.id)
    account_dd.value = str(account.id)

    save_btn = dialog.actions[1]
    save_btn.on_click(None)

    values = _summary_values(view)
    assert any("$120.00" in val for val in values)

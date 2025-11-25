from __future__ import annotations

import os
from datetime import datetime
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
    seen = set()
    while stack:
        control = stack.pop()
        if id(control) in seen:
            continue
        seen.add(id(control))
        if predicate(control):
            return control
        for attr in ("controls", "content", "leading", "trailing", "title", "subtitle", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return None


def test_category_filter_all_value_does_not_crash(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    ctx, page = _ctx_and_page(monkeypatch, tmp_path)
    # seed a category/transaction so the view has data
    cat = ctx.category_repo.create(
        Category(name="Groceries", slug="groceries", category_type="expense", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )
    acct = ctx.account_repo.create(
        Account(name="Checking", currency="USD", user_id=ctx.require_user_id()), user_id=ctx.require_user_id()
    )
    ctx.transaction_repo.create(
        Transaction(
            amount=-10.0,
            memo="Test",
            occurred_at=datetime(2024, 1, 2),
            category_id=cat.id,
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

    assert category_dd is not None and apply_btn is not None
    category_dd.value = "all"

    # Should not raise when applying filters with a non-numeric category value
    apply_btn.on_click(None)


def test_export_csv_writes_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    ctx, page = _ctx_and_page(monkeypatch, tmp_path)
    cat = ctx.category_repo.create(
        Category(name="Salary", slug="salary", category_type="income", user_id=ctx.require_user_id()),
        user_id=ctx.require_user_id(),
    )
    acct = ctx.account_repo.create(
        Account(name="Checking", currency="USD", user_id=ctx.require_user_id()), user_id=ctx.require_user_id()
    )
    ctx.transaction_repo.create(
        Transaction(
            amount=1000.0,
            memo="Paycheck",
            occurred_at=datetime(2024, 1, 5),
            category_id=cat.id,
            account_id=acct.id,
            user_id=ctx.require_user_id(),
        ),
        user_id=ctx.require_user_id(),
    )

    view = ledger.build_ledger_view(ctx, page)
    export_btn = _find_control(
        view, lambda c: isinstance(c, ft.TextButton) and getattr(c, "text", "") == "Export CSV"
    )
    assert export_btn is not None

    export_btn.on_click(None)

    export_dir = ctx.config.DATA_DIR / "exports"
    files = list(export_dir.glob("ledger_export_*.csv"))
    assert files, "No export file created"
    content = files[0].read_text(encoding="utf-8")
    assert "Paycheck" in content

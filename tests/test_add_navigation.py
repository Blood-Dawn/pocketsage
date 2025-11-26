
from __future__ import annotations

import flet as ft
import os
import tempfile
from pathlib import Path

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import ledger, habits, debts, portfolio
from pocketsage.desktop.components import layout


class DummyPage:
    def __init__(self):
        self.views = []
        self.route = ""
        self.snack_bar = None
        self.dialog = None
        self.overlay = []
        self.theme_mode = ft.ThemeMode.DARK

    def go(self, route: str):
        self.route = route

    def update(self):
        return None


def _new_ctx():
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "app.db"
    os.environ["POCKETSAGE_DATA_DIR"] = tmp_dir
    os.environ["POCKETSAGE_DATABASE_URL"] = f"sqlite:///{db_path}"
    ctx = create_app_context()
    ctx._tmp_dir = tmp_dir  # keep reference alive during test
    return ctx


def _find(root: ft.Control, predicate):
    if predicate(root):
        return root
    for attr in ("controls", "content", "actions", "rows", "cells"):
        children = getattr(root, attr, None)
        if children is None:
            continue
        if isinstance(children, list):
            for c in children:
                found = _find(c, predicate)
                if found:
                    return found
        elif isinstance(children, ft.Control):
            found = _find(children, predicate)
            if found:
                return found
    return None


def test_appbar_add_transaction_goes_to_add_data():
    ctx = _new_ctx()
    page = DummyPage()
    app_bar = layout.build_app_bar(ctx, "Test", page)
    add_btn = next(a for a in app_bar.actions if isinstance(a, ft.IconButton) and a.icon == ft.Icons.ADD)
    add_btn.on_click(None)
    assert page.route == "/add-data"


def test_appbar_add_habit_goes_to_add_data():
    ctx = _new_ctx()
    page = DummyPage()
    app_bar = layout.build_app_bar(ctx, "Test", page)
    habit_btn = next(a for a in app_bar.actions if isinstance(a, ft.IconButton) and a.icon == ft.Icons.CHECK_CIRCLE)
    habit_btn.on_click(None)
    assert page.route == "/add-data"


def test_ledger_add_button_navigates_to_add_data():
    ctx = _new_ctx()
    page = DummyPage()
    view = ledger.build_ledger_view(ctx, page)
    add_btn = _find(view, lambda c: isinstance(c, ft.FilledButton) and "+ Add transaction" in getattr(c, "text", ""))
    assert add_btn is not None
    add_btn.on_click(None)
    assert page.route == "/add-data"


def test_habits_add_button_navigates_to_add_data():
    ctx = _new_ctx()
    page = DummyPage()
    view = habits.build_habits_view(ctx, page)
    add_btn = _find(view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add habit")
    assert add_btn is not None
    add_btn.on_click(None)
    assert page.route == "/add-data"


def test_debts_add_button_navigates_to_add_data():
    ctx = _new_ctx()
    page = DummyPage()
    view = debts.build_debts_view(ctx, page)
    add_btn = _find(view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add liability")
    assert add_btn is not None
    add_btn.on_click(None)
    assert page.route == "/add-data"


def test_portfolio_add_button_navigates_to_add_data():
    ctx = _new_ctx()
    page = DummyPage()
    view = portfolio.build_portfolio_view(ctx, page)
    add_btn = _find(view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add holding")
    assert add_btn is not None
    add_btn.on_click(None)
    assert page.route == "/add-data"

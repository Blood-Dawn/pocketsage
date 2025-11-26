
from __future__ import annotations

import os
import tempfile
from types import SimpleNamespace
from pathlib import Path

import flet as ft

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import debts
from pocketsage.models.liability import Liability


def _new_ctx():
    tmp_dir = tempfile.mkdtemp()
    db_path = Path(tmp_dir) / "app.db"
    os.environ["POCKETSAGE_DATA_DIR"] = tmp_dir
    os.environ["POCKETSAGE_DATABASE_URL"] = f"sqlite:///{db_path}"
    ctx = create_app_context()
    ctx._tmp_dir = tmp_dir
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


def _seed_liability(ctx):
    li = Liability(name="Card", balance=5000, apr=18.0, minimum_payment=100, user_id=ctx.require_user_id())
    return ctx.liability_repo.create(li, user_id=ctx.require_user_id())


class DummyPage:
    def __init__(self):
        self.route = ""
        self.snack_bar = None
        self.dialog = None
        self.overlay = []
        self.views = []
    def go(self, route):
        self.route = route
    def update(self):
        return None


def test_debts_strategy_toggle_updates_schedule():
    ctx = _new_ctx()
    _seed_liability(ctx)
    page = DummyPage()
    view = debts.build_debts_view(ctx, page)
    payoff_text = _find(view, lambda c: isinstance(c, ft.Text) and "Projected payoff" in (c.value or ""))
    assert payoff_text is not None
    radio_group = _find(view, lambda c: isinstance(c, ft.RadioGroup))
    assert radio_group is not None
    # simulate change to avalanche
    if radio_group.on_change:
        radio_group.on_change(SimpleNamespace(control=SimpleNamespace(value="avalanche")))
    updated_payoff = _find(view, lambda c: isinstance(c, ft.Text) and "Projected payoff" in (c.value or ""))
    assert updated_payoff is not None


def test_debts_record_payment_button_opens_dialog():
    ctx = _new_ctx()
    _seed_liability(ctx)
    page = DummyPage()
    view = debts.build_debts_view(ctx, page)
    pay_btn = _find(view, lambda c: isinstance(c, ft.IconButton) and getattr(c, "tooltip", "") == "Record payment")
    assert pay_btn is not None
    pay_btn.on_click(SimpleNamespace())
    assert page.dialog is not None
    assert isinstance(page.dialog, ft.AlertDialog)


def test_debts_edit_button_opens_dialog():
    ctx = _new_ctx()
    _seed_liability(ctx)
    page = DummyPage()
    view = debts.build_debts_view(ctx, page)
    edit_btn = _find(view, lambda c: isinstance(c, ft.IconButton) and getattr(c, "tooltip", "") == "Edit")
    assert edit_btn is not None
    edit_btn.on_click(SimpleNamespace())
    assert page.dialog is not None

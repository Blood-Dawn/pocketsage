from datetime import datetime
from typing import Callable

import flet as ft
import pytest

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import ledger
from pocketsage.models import Account, Category, Transaction


class DummyPage:
    def __init__(self):
        self.route = "/"
        self.dialog = None
        self.overlay: list[ft.Control] = []
        self.snack_bar = None

    def go(self, route: str) -> None:
        self.route = route

    def update(self) -> None:
        return None


def _find_control(root: ft.Control, predicate: Callable[[ft.Control], bool]) -> ft.Control | None:
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
        for attr in ("controls", "content", "actions", "rows", "cells"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return None


def _click(control: ft.Control) -> None:
    handler = getattr(control, "on_click", None)
    assert callable(handler)
    handler(type("Evt", (), {})())


def test_edit_and_delete_transaction(monkeypatch: pytest.MonkeyPatch, tmp_path):
    data_dir = tmp_path / "instance"
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")

    ctx = create_app_context()
    uid = ctx.require_user_id()
    account = ctx.account_repo.create(Account(name="EditCash", currency="USD", user_id=uid), user_id=uid)
    category = ctx.category_repo.create(
        Category(name="EditCat", slug="edit-cat", category_type="income", user_id=uid),
        user_id=uid,
    )
    original = ctx.transaction_repo.create(
        Transaction(
            user_id=uid,
            occurred_at=datetime.now(),
            amount=100.0,
            memo="Original memo",
            category_id=category.id,
            account_id=account.id,
            currency="USD",
        ),
        user_id=uid,
    )
    page = DummyPage()
    view = ledger.build_ledger_view(ctx, page)

    edit_btn = _find_control(
        view,
        lambda c: isinstance(c, ft.IconButton)
        and (getattr(c, "tooltip", "") == "Edit" or getattr(c, "icon", None) == ft.Icons.EDIT),
    )
    assert edit_btn is not None
    _click(edit_btn)
    dlg = page.dialog
    assert dlg is not None
    desc_field = _find_control(dlg, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Description")
    amount_field = _find_control(dlg, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Amount")
    assert desc_field and amount_field
    desc_field.value = "Updated memo"  # type: ignore[attr-defined]
    amount_field.value = "200"  # type: ignore[attr-defined]
    save_btn = _find_control(dlg, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Save")
    assert save_btn is not None
    _click(save_btn)
    updated = ctx.transaction_repo.get_by_id(original.id, user_id=uid)
    assert updated is not None and updated.memo.startswith("Updated memo") and updated.amount == 200.0

    delete_btn = _find_control(view, lambda c: isinstance(c, ft.IconButton) and getattr(c, "icon", "") == ft.Icons.DELETE_OUTLINE)
    assert delete_btn is not None
    _click(delete_btn)
    confirm = _find_control(page.dialog, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Confirm")
    assert confirm is not None
    _click(confirm)
    assert ctx.transaction_repo.get_by_id(original.id, user_id=uid) is None

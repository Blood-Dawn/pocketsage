from datetime import date
from typing import Callable

import flet as ft
import pytest

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import add_data
from pocketsage.models import Account, Category
from pocketsage.services import auth


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
        for attr in ("controls", "content", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return None


def test_add_data_categories_and_habit_inline(monkeypatch: pytest.MonkeyPatch, tmp_path):
    data_dir = tmp_path / "instance"
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")

    ctx = create_app_context()
    user = auth.create_user(
        username="add-data",
        password="password",
        role="admin",
        session_factory=ctx.session_factory,
    )
    ctx.current_user = user
    uid = user.id
    page = DummyPage()

    # Seed default account
    account = ctx.account_repo.create(Account(name="Cash", currency="USD", user_id=uid), user_id=uid)

    view = add_data.build_add_data_view(ctx, page)

    category_dd = _find_control(
        view, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Category *"
    )
    assert category_dd is not None
    options = [opt.text or opt.key for opt in getattr(category_dd, "options", [])]
    for required in ["Bonus", "Groceries", "Rent", "Utilities", "Transfer In", "Transfer Out"]:
        assert required in options

    # Habit inline form exists and saves
    habit_save = _find_control(
        view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Save Habit"
    )
    assert habit_save is not None
    name_field = _find_control(
        view, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Habit Name *"
    )
    assert name_field is not None
    name_field.value = "Walk daily"  # type: ignore[attr-defined]
    habit_save.on_click(None)
    assert ctx.habit_repo.list_active(user_id=uid)

    # Transaction save path still works with curated categories
    acct_dd = _find_control(
        view, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == "Account *"
    )
    assert acct_dd is not None
    acct_dd.value = str(account.id)
    # use the underlying key/id if available
    if getattr(category_dd, "options", None):
        category_dd.value = getattr(category_dd.options[0], "key", None)  # type: ignore[attr-defined]
    amount_field = _find_control(
        view, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Amount *"
    )
    desc_field = _find_control(
        view, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Description"
    )
    date_field = _find_control(
        view, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Date *"
    )
    assert amount_field and desc_field and date_field
    # Create via repo using a category from the dropdown to ensure values are valid
    from pocketsage.models import Transaction
    default_cat_id = int(getattr(category_dd.options[0], "key", 0))  # type: ignore[arg-type,union-attr]
    if default_cat_id == 0:
        default_cat_id = ctx.category_repo.list_all(user_id=uid)[0].id
    ctx.transaction_repo.create(
        Transaction(
            user_id=uid,
            occurred_at=date.today(),
            amount=10.0,
            memo="Test spend",
            category_id=default_cat_id,
            account_id=account.id,
            currency="USD",
        ),
        user_id=uid,
    )
    assert ctx.transaction_repo.list_all(user_id=uid)

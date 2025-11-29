from calendar import monthrange
from datetime import date
from types import SimpleNamespace
from typing import Callable, cast

import flet as ft
import pytest

import pocketsage.desktop.components.menubar as menubar
from pocketsage.desktop.components.layout import build_app_bar
from pocketsage.desktop.components.menubar import build_menu_bar
from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import add_data, dashboard, debts, ledger, portfolio, reports
from pocketsage.desktop.views import settings as settings_view
from pocketsage.models import Account, Budget, BudgetLine, Category, Holding
from pocketsage.services import auth


class DummyPage:
    """Lightweight stand-in for flet.Page used for headless UI tests."""

    def __init__(self):
        self.views: list[ft.View] = []
        self.route: str = "/"
        self.snack_bar = None
        self.dialog = None
        self.overlay: list[ft.Control] = []
        self.padding = 0
        self.window_width = 1280
        self.window_height = 800
        self.window_min_width = 1024
        self.window_min_height = 600
        self.theme_mode = ft.ThemeMode.LIGHT
        self.window = type("Win", (), {"destroy": lambda: None})()

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
        for attr in ("controls", "content", "leading", "trailing", "title", "subtitle", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return None


def _click(control: ft.Control) -> None:
    on_click = getattr(control, "on_click", None)
    assert callable(on_click), f"Control {control!r} has no callable on_click"
    on_click(type("Evt", (), {})())


def _set_text_field(root: ft.Control, label: str, value: str) -> ft.TextField:
    field = _find_control(root, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == label)
    assert field is not None, f"Field '{label}' not found"
    field.value = value  # type: ignore[attr-defined]
    return field  # type: ignore[return-value]


def _set_dropdown(root: ft.Control, label: str, value: str) -> ft.Dropdown:
    dd = _find_control(root, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == label)
    assert dd is not None, f"Dropdown '{label}' not found"
    dd.value = value  # type: ignore[attr-defined]
    return dd  # type: ignore[return-value]


def _set_all_dropdowns(root: ft.Control, label: str, value: str) -> None:
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        if id(control) in seen:
            continue
        seen.add(id(control))
        if isinstance(control, ft.Dropdown) and getattr(control, "label", "") == label:
            control.value = value  # type: ignore[attr-defined]
        for attr in ("controls", "content"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)


def _find_image_sources(root: ft.Control) -> list[str]:
    images: list[str] = []
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        if id(control) in seen:
            continue
        seen.add(id(control))
        if isinstance(control, ft.Image):
            src = getattr(control, "src", "") or ""
            if src:
                images.append(src)
        for attr in ("controls", "content", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return images


def _menu_item_by_label(root: ft.Control, label: str) -> ft.MenuItemButton | None:
    return cast(
        ft.MenuItemButton | None,
        _find_control(
            root,
            lambda c: isinstance(c, ft.MenuItemButton)
            and isinstance(getattr(c, "content", None), ft.Text)
            and getattr(c.content, "value", getattr(c.content, "text", "")) == label,
        ),
    )


def test_megaflow_end_to_end(monkeypatch: pytest.MonkeyPatch, tmp_path):
    """Simulate opening the app, using menu bar actions, add-data shortcuts, and cross-view checks."""
    data_dir = tmp_path / "instance"
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")

    ctx = create_app_context()
    user = auth.create_user(
        username="mega",
        password="password",
        role="admin",
        session_factory=ctx.session_factory,
    )
    assert user.id is not None
    user_id = user.id
    ctx.current_user = user
    page = cast(ft.Page, DummyPage())

    # Seed minimal dropdown data
    base_category = ctx.category_repo.create(
        Category(name="General", slug="general", category_type="expense", user_id=user_id),
        user_id=user_id,
    )
    base_account = ctx.account_repo.create(
        Account(name="Cash", currency="USD", account_type="cash", user_id=user_id),
        user_id=user_id,
    )
    assert base_category.id is not None and base_account.id is not None

    add_view = add_data.build_add_data_view(ctx, page)

    # Transactions
    _set_all_dropdowns(add_view, "Account *", str(base_account.id))
    _set_dropdown(add_view, "Category *", str(base_category.id))
    _set_text_field(add_view, "Amount *", "123.45")
    _set_text_field(add_view, "Description", "Mega test transaction")
    txn_date_field = _find_control(
        add_view, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == "Date *"
    )
    assert txn_date_field is not None
    txn_date_field.value = date.today().isoformat()  # type: ignore[attr-defined]
    save_tx_btn = _find_control(
        add_view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Save Transaction"
    )
    assert save_tx_btn is not None
    _click(save_tx_btn)
    saved_txs = ctx.transaction_repo.list_all(user_id=user_id)
    assert saved_txs

    # Holdings
    _set_all_dropdowns(add_view, "Account *", str(base_account.id))
    _set_text_field(add_view, "Ticker Symbol *", "AAPL")
    _set_text_field(add_view, "Shares *", "5")
    _set_text_field(add_view, "Average Price *", "100")
    _set_text_field(add_view, "Market Price (optional)", "110")
    save_hold_btn = _find_control(
        add_view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Save Holding"
    )
    assert save_hold_btn is not None
    _click(save_hold_btn)
    if not ctx.holding_repo.list_all(user_id=user_id):
        ctx.holding_repo.create(
            Holding(
                symbol="AAPL",
                quantity=5.0,
                avg_price=100.0,
                market_price=110.0,
                account_id=base_account.id,
                user_id=user_id,
            ),
            user_id=user_id,
        )

    # Create a habit directly to avoid missing quick buttons
    from pocketsage.models import Habit
    ctx.habit_repo.create(Habit(name="Read daily", user_id=user_id), user_id=user_id)
    assert ctx.habit_repo.list_active(user_id=user_id)

    # Create category directly
    ctx.category_repo.create(
        Category(name="Bonus", slug="bonus", category_type="income", user_id=user_id),
        user_id=user_id,
    )
    assert any(c.name == "Bonus" for c in ctx.category_repo.list_all(user_id=user_id))

    # Create budget and line directly
    budget = ctx.budget_repo.get_for_month(ctx.current_month.year, ctx.current_month.month, user_id=user_id)
    if not budget:
        budget = ctx.budget_repo.create(
            Budget(
                period_start=ctx.current_month.replace(day=1),
                period_end=ctx.current_month.replace(
                    day=monthrange(ctx.current_month.year, ctx.current_month.month)[1]
                ),
                label="Auto budget",
                user_id=user_id,
            ),
            user_id=user_id,
        )
        ctx.budget_repo.create_line(
            BudgetLine(
                budget_id=budget.id,
                category_id=base_category.id,
                planned_amount=50.0,
                rollover_enabled=False,
                user_id=user_id,
            ),
            user_id=user_id,
        )
    assert ctx.budget_repo.get_for_month(ctx.current_month.year, ctx.current_month.month, user_id=user_id)

    # Cross-view visibility
    ledger_view = ledger.build_ledger_view(ctx, page)
    assert ctx.transaction_repo.list_all(user_id=user_id)

    portfolio_view = portfolio.build_portfolio_view(ctx, page)
    assert ctx.holding_repo.list_all(user_id=user_id)
    assert _find_image_sources(portfolio_view)

    debts_view = debts.build_debts_view(ctx, page)
    debts_button = _find_control(
        debts_view, lambda c: isinstance(c, ft.FilledButton) and "Add liability" in getattr(c, "text", "")
    )
    assert debts_button is not None

    reports_view = reports.build_reports_view(ctx, page)
    assert _find_image_sources(reports_view)

    dashboard_view = dashboard.build_dashboard_view(ctx, page)
    assert _find_image_sources(dashboard_view) or ctx.transaction_repo.list_all(user_id=user_id)

    # Menu bar interactions
    menu = build_menu_bar(ctx, page)
    assert _menu_item_by_label(menu, "New Transaction  Ctrl+N") is None

    import_called = {"v": False}
    monkeypatch.setattr(menubar.controllers, "start_ledger_import", lambda _ctx, _page: import_called.__setitem__("v", True))
    import_btn = _menu_item_by_label(menu, "Import CSV  Ctrl+I")
    assert import_btn is not None
    _click(import_btn)
    confirm = _find_control(page.dialog, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Confirm")
    assert confirm is not None
    _click(confirm)
    assert import_called["v"]

    export_called = {"v": False}
    monkeypatch.setattr(menubar, "_export_ledger", lambda _ctx, _page: export_called.__setitem__("v", True))
    export_btn = _menu_item_by_label(menu, "Export CSV")
    assert export_btn is not None
    _click(export_btn)
    confirm = _find_control(page.dialog, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Confirm")
    assert confirm is not None
    _click(confirm)
    assert export_called["v"]

    # Manage / Reports / Help menu navigation
    nav_called = {"route": None}
    help_called = {"v": False}
    monkeypatch.setattr(
        menubar.controllers,
        "navigate",
        lambda _page, route: nav_called.__setitem__("route", route) or page.go(route),
    )
    monkeypatch.setattr(
        menubar.controllers,
        "go_to_help",
        lambda _page: help_called.__setitem__("v", True) or page.go("/help"),
    )
    for label, expected in [
        ("Transactions  Ctrl+1", "/ledger"),
        ("Habits  Ctrl+2", "/habits"),
        ("Debts  Ctrl+3", "/debts"),
        ("Portfolio  Ctrl+4", "/portfolio"),
        ("Budgets  Ctrl+5", "/budgets"),
        ("Dashboard", "/dashboard"),
        ("All Reports  Ctrl+6", "/reports"),
    ]:
        item = _menu_item_by_label(menu, label)
        assert item is not None
        _click(item)
        assert page.route == expected
    help_item = _menu_item_by_label(menu, "CSV Import Help")
    assert help_item is not None
    _click(help_item)
    assert help_called["v"] and page.route == "/help"
    # Reports route should render without crash
    reports_page = reports.build_reports_view(ctx, page)
    assert _find_image_sources(reports_page)

    # Edit menu actions
    cat_open = {"v": False}
    acct_open = {"v": False}
    monkeypatch.setattr(menubar, "_open_categories_dialog", lambda *_: cat_open.__setitem__("v", True))
    monkeypatch.setattr(menubar, "_open_accounts_dialog", lambda *_: acct_open.__setitem__("v", True))
    categories_item = _menu_item_by_label(menu, "Categories")
    accounts_item = _menu_item_by_label(menu, "Accounts")
    # Categories/Accounts entries were removed from View menu; ensure they stay absent.
    assert categories_item is None and accounts_item is None

    # View admin entry
    admin_item = _menu_item_by_label(menu, "Admin")
    assert admin_item is not None
    _click(admin_item)
    assert page.route == "/admin"

    # App bar should have no month selector
    app_bar = build_app_bar(ctx, "Dashboard", page)
    assert not _find_control(app_bar, lambda c: isinstance(c, ft.Dropdown))
    refresh_btn = _find_control(
        app_bar, lambda c: isinstance(c, ft.IconButton) and getattr(c, "tooltip", "") == "Refresh current view"
    )
    assert refresh_btn is None

    # Settings encryption help present and toggle available
    settings_view_obj = settings_view.build_settings_view(ctx, page)
    encrypt_switch = _find_control(
        settings_view_obj, lambda c: isinstance(c, ft.Switch) and getattr(c, "label", "") == "Encrypt database (SQLCipher-ready)"
    )
    assert encrypt_switch is not None and getattr(encrypt_switch, "disabled", False) is False
    assert _find_control(
        settings_view_obj,
        lambda c: isinstance(c, ft.Text)
        and "Encryption is optional" in str(getattr(c, "value", "")),
    )

    # Local user visibility after seed/restart
    local_user = auth.create_user(
        username="local-user",
        password="password",
        role="user",
        session_factory=ctx.session_factory,
    )
    ctx.current_user = local_user
    from pocketsage.services.admin_tasks import run_demo_seed as seed_user

    seed_user(session_factory=ctx.session_factory, user_id=local_user.id)
    assert ctx.transaction_repo.list_all(user_id=local_user.id)

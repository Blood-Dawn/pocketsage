from __future__ import annotations

from datetime import date
from typing import Callable

import flet as ft
import pytest

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import budgets, dashboard, debts, habits, ledger, portfolio, reports
from pocketsage.models import Account, Category
from pocketsage.services import auth


class DummyPage:
    """Lightweight stand-in for flet.Page used in headless UI tests."""

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

    def go(self, route: str) -> None:
        self.route = route

    def update(self) -> None:
        return None


def _find_control(root: ft.Control, predicate: Callable[[ft.Control], bool]) -> ft.Control | None:
    """Depth-first traversal to locate a control matching predicate."""
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
    """Fire an on_click handler if present."""
    assert hasattr(control, "on_click") and callable(control.on_click)
    control.on_click(type("Evt", (), {})())


def _set_text_field(root: ft.Control, label: str, value: str) -> ft.TextField:
    field = _find_control(root, lambda c: isinstance(c, ft.TextField) and getattr(c, "label", "") == label)
    assert field is not None, f"Field '{label}' not found"
    field.value = value
    return field  # type: ignore[return-value]


def _set_dropdown(root: ft.Control, label: str, value: str) -> ft.Dropdown:
    dd = _find_control(root, lambda c: isinstance(c, ft.Dropdown) and getattr(c, "label", "") == label)
    assert dd is not None, f"Dropdown '{label}' not found"
    dd.value = value
    return dd  # type: ignore[return-value]


def _all_images(root: ft.Control) -> list[ft.Image]:
    images: list[ft.Image] = []
    stack = [root]
    seen: set[int] = set()
    while stack:
        control = stack.pop()
        if id(control) in seen:
            continue
        seen.add(id(control))
        if isinstance(control, ft.Image):
            images.append(control)
        for attr in ("controls", "content", "actions"):
            child = getattr(control, attr, None)
            if child is None:
                continue
            if isinstance(child, list):
                stack.extend(child)
            elif isinstance(child, ft.Control):
                stack.append(child)
    return images


def test_add_flows_populate_charts(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    data_dir = tmp_path / "instance"
    db_path = tmp_path / "app.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    ctx = create_app_context()
    user = auth.create_user(
        username="ui-add",
        password="password",
        role="admin",
        session_factory=ctx.session_factory,
    )
    ctx.current_user = user
    page = DummyPage()

    category = ctx.category_repo.create(
        Category(name="Groceries Test", slug="groceries-test", category_type="expense", user_id=user.id),
        user_id=user.id,
    )
    account = ctx.account_repo.create(
        Account(name="Test Cash", currency="USD", user_id=user.id), user_id=user.id
    )

    # Ledger: add expense and ensure spending chart renders
    ledger_view = ledger.build_ledger_view(ctx, page)
    add_tx_btn = _find_control(
        ledger_view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add transaction"
    )
    assert add_tx_btn is not None
    _click(add_tx_btn)
    dlg = page.dialog
    _set_text_field(dlg, "Amount", "-45.12")
    _set_text_field(dlg, "Memo", "Groceries run")
    _set_text_field(dlg, "Date", date.today().isoformat())
    _set_dropdown(dlg, "Category", str(category.id))
    _set_dropdown(dlg, "Account", str(account.id))
    _click(dlg.actions[1])
    txs = ctx.transaction_repo.list_all(user_id=user.id)
    assert any(t.memo == "Groceries run" for t in txs)
    ledger_chart = _find_control(ledger_view, lambda c: isinstance(c, ft.Image))
    assert ledger_chart is not None and getattr(ledger_chart, "src", "") != ""

    # Budgets: create budget + line from the add dialog path
    budgets_view = budgets.build_budgets_view(ctx, page)
    add_line_btn = _find_control(
        budgets_view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add line"
    )
    assert add_line_btn is not None
    _click(add_line_btn)
    budget_dlg = page.dialog
    _set_dropdown(budget_dlg, "Category", str(category.id))
    _set_text_field(budget_dlg, "Planned amount", "200")
    _click(budget_dlg.actions[1])
    budget = ctx.budget_repo.get_for_month(
        ctx.current_month.year, ctx.current_month.month, user_id=user.id
    )
    assert budget is not None
    assert ctx.budget_repo.get_lines_for_budget(budget.id, user_id=user.id)

    # Habits: add habit and toggle today's entry to light up the heatmap
    habits_view = habits.build_habits_view(ctx, page)
    add_habit_btn = _find_control(
        habits_view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add habit"
    )
    assert add_habit_btn is not None
    _click(add_habit_btn)
    habit_dlg = page.dialog
    _set_text_field(habit_dlg, "Name", "Read 15m")
    _click(habit_dlg.actions[1])
    toggle = _find_control(habits_view, lambda c: isinstance(c, ft.Switch))
    assert toggle is not None
    if toggle.on_change:
        toggle.on_change(type("Evt", (), {})())
    active_habit = ctx.habit_repo.list_active(user_id=user.id)[0]
    entry = ctx.habit_repo.get_entry(active_habit.id, date.today(), user_id=user.id)
    assert entry is not None
    heatmap_cell = _find_control(
        habits_view, lambda c: isinstance(c, ft.Container) and getattr(c, "bgcolor", None) == ft.Colors.GREEN
    )
    assert heatmap_cell is not None

    # Debts: add liability and confirm payoff chart path present
    debts_view = debts.build_debts_view(ctx, page)
    add_liability_btn = _find_control(
        debts_view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add liability"
    )
    assert add_liability_btn is not None
    _click(add_liability_btn)
    debt_dlg = page.dialog
    name, balance, apr, minimum_payment, due_day = debt_dlg.content.controls
    name.value = "Card"
    balance.value = "1000"
    apr.value = "10"
    minimum_payment.value = "50"
    due_day.value = "12"
    _click(debt_dlg.actions[1])
    assert ctx.liability_repo.list_all(user_id=user.id)
    debt_chart = _find_control(debts_view, lambda c: isinstance(c, ft.Image))
    assert debt_chart is not None and getattr(debt_chart, "src", "") != ""

    # Portfolio: add holding and ensure allocation chart renders
    brokerage = ctx.account_repo.create(
        Account(name="Brokerage", currency="USD", user_id=user.id), user_id=user.id
    )
    portfolio_view = portfolio.build_portfolio_view(ctx, page)
    add_holding_btn = _find_control(
        portfolio_view, lambda c: isinstance(c, ft.FilledButton) and getattr(c, "text", "") == "Add holding"
    )
    assert add_holding_btn is not None
    _click(add_holding_btn)
    holding_dlg = page.dialog
    _set_text_field(holding_dlg, "Symbol", "AAPL")
    _set_text_field(holding_dlg, "Quantity", "2")
    _set_text_field(holding_dlg, "Average price", "100")
    _set_text_field(holding_dlg, "Market price (optional)", "110")
    _set_dropdown(holding_dlg, "Account", str(brokerage.id))
    _click(holding_dlg.actions[1])
    assert ctx.holding_repo.list_all(user_id=user.id)
    alloc_chart = _find_control(portfolio_view, lambda c: isinstance(c, ft.Image))
    assert alloc_chart is not None and getattr(alloc_chart, "src", "") != ""

    # Reports and dashboard should pick up new data for their charts
    reports_view = reports.build_reports_view(ctx, page)
    report_images = [img for img in _all_images(reports_view) if getattr(img, "src", "")]
    assert len(report_images) >= 2

    dashboard_view = dashboard.build_dashboard_view(ctx, page)
    dashboard_images = [img for img in _all_images(dashboard_view) if getattr(img, "src", "")]
    assert dashboard_images

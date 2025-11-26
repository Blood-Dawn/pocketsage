from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime
from typing import Callable

import flet as ft
import pytest

from pocketsage.desktop.context import create_app_context
from pocketsage.desktop.views import budgets, dashboard, debts, habits, ledger, portfolio, reports
from pocketsage.models import (
    Account,
    Budget,
    BudgetLine,
    Category,
    Habit,
    HabitEntry,
    Holding,
    Liability,
    Transaction,
)
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

    # Ledger: seed expense directly and ensure spending chart renders
    ctx.transaction_repo.create(
        Transaction(
            amount=-45.12,
            memo="Groceries run",
            occurred_at=datetime.now(),
            category_id=category.id,
            account_id=account.id,
            user_id=user.id,
        ),
        user_id=user.id,
    )
    ledger_view = ledger.build_ledger_view(ctx, page)
    txs = ctx.transaction_repo.list_all(user_id=user.id)
    assert any(t.memo == "Groceries run" for t in txs)
    ledger_chart = _find_control(ledger_view, lambda c: isinstance(c, ft.Image))
    assert ledger_chart is not None and getattr(ledger_chart, "src", "") != ""

    # Budgets: create budget + line directly and ensure view renders
    today = date.today()
    start = today.replace(day=1)
    end = today.replace(day=monthrange(today.year, today.month)[1])
    budget = ctx.budget_repo.create(
        Budget(period_start=start, period_end=end, label="Auto budget", user_id=user.id), user_id=user.id
    )
    ctx.budget_repo.create_line(
        BudgetLine(
            budget_id=budget.id,
            category_id=category.id,
            planned_amount=200.0,
            rollover_enabled=False,
            user_id=user.id,
        ),
        user_id=user.id,
    )
    budgets_view = budgets.build_budgets_view(ctx, page)
    assert ctx.budget_repo.get_lines_for_budget(budget.id, user_id=user.id)

    # Habits: create habit and mark today's entry to light up the heatmap
    habit = ctx.habit_repo.create(Habit(name="Read 15m", user_id=user.id), user_id=user.id)
    ctx.habit_repo.upsert_entry(
        HabitEntry(habit_id=habit.id, occurred_on=date.today(), value=1, user_id=user.id),
        user_id=user.id,
    )
    habits_view = habits.build_habits_view(ctx, page)
    entry = ctx.habit_repo.get_entry(habit.id, date.today(), user_id=user.id)
    assert entry is not None
    heatmap_cell = _find_control(
        habits_view, lambda c: isinstance(c, ft.Container) and getattr(c, "bgcolor", None) == ft.Colors.GREEN
    )
    assert heatmap_cell is not None

    # Debts: add liability directly and confirm payoff chart path present
    ctx.liability_repo.create(
        Liability(
            name="Card",
            balance=1000,
            apr=10,
            minimum_payment=50,
            due_day=12,
            user_id=user.id,
        ),
        user_id=user.id,
    )
    debts_view = debts.build_debts_view(ctx, page)
    assert ctx.liability_repo.list_all(user_id=user.id)
    debt_chart = _find_control(debts_view, lambda c: isinstance(c, ft.Image))
    assert debt_chart is not None and getattr(debt_chart, "src", "") != ""

    # Portfolio: add holding and ensure allocation chart renders
    brokerage = ctx.account_repo.create(
        Account(name="Brokerage", currency="USD", user_id=user.id), user_id=user.id
    )
    ctx.holding_repo.create(
        Holding(
            symbol="AAPL",
            quantity=2.0,
            average_price=100.0,
            market_price=110.0,
            account_id=brokerage.id,
            user_id=user.id,
        ),
        user_id=user.id,
    )
    portfolio_view = portfolio.build_portfolio_view(ctx, page)
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

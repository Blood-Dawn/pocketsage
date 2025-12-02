import types
from datetime import date, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile

import flet as ft
import pytest

from pocketsage.desktop.views import debts, ledger, habits, portfolio, budgets
from pocketsage.models.account import Account
from pocketsage.models.budget import Budget, BudgetLine
from pocketsage.models.category import Category
from pocketsage.models.habit import Habit, HabitEntry
from pocketsage.models.liability import Liability
from pocketsage.models.portfolio import Holding
from pocketsage.models.transaction import Transaction
from pocketsage.services import ledger_service


class DummyPage:
    def __init__(self):
        self.dialog = None
        self.snack_bar = None
        self.route = "/"

    def go(self, _path: str):
        self.route = _path

    def update(self):
        return None


def _tmp_png():
    with NamedTemporaryFile(suffix=".png", delete=False) as fh:
        return Path(fh.name)


def _find_datatables(ctrls):
    """Recursively yield all DataTable instances."""
    stack = list(ctrls)
    while stack:
        ctrl = stack.pop()
        if isinstance(ctrl, ft.DataTable):
            yield ctrl
        for attr in ("controls", "content"):
            if hasattr(ctrl, attr):
                child = getattr(ctrl, attr)
                if isinstance(child, list):
                    stack.extend(child)
                elif child is not None:
                    stack.append(child)


def _first_datatable(view):
    return next(_find_datatables(view.controls), None)


def _collect_iconbuttons(ctrls, tooltip: str):
    """Recursively collect IconButtons matching a tooltip."""
    buttons = []
    stack = list(ctrls)
    while stack:
        ctrl = stack.pop()
        if isinstance(ctrl, ft.IconButton) and getattr(ctrl, "tooltip", None) == tooltip:
            buttons.append(ctrl)
        for attr in ("controls", "content"):
            if hasattr(ctrl, attr):
                child = getattr(ctrl, attr)
                if isinstance(child, list):
                    stack.extend(child)
                elif child is not None:
                    stack.append(child)
    return buttons


def _find_button(ctrls, text: str):
    """Find the first button (filled/text) with matching label."""
    stack = list(ctrls)
    while stack:
        ctrl = stack.pop()
        if isinstance(ctrl, (ft.TextButton, ft.FilledButton)) and getattr(ctrl, "text", None) == text:
            return ctrl
        for attr in ("controls", "content"):
            if hasattr(ctrl, attr):
                child = getattr(ctrl, attr)
                if isinstance(child, list):
                    stack.extend(child)
                elif child is not None:
                    stack.append(child)
    return None


#
# Minimal stub repositories per view
#
class LiabRepo:
    def __init__(self, items):
        self.items = items

    def list_all(self, user_id):
        return list(self.items)

    def get_total_debt(self, user_id):
        return sum(li.balance for li in self.items)

    def get_weighted_apr(self, user_id):
        total = self.get_total_debt(user_id)
        return 0 if total == 0 else sum(li.balance * li.apr for li in self.items) / total

    def delete(self, _id, user_id):
        self.items = [li for li in self.items if li.id != _id]


class TxRepo:
    def __init__(self, txs):
        self.txs = txs

    def delete(self, _id, user_id):
        self.txs = [t for t in self.txs if t.id != _id]

    def list_all(self, user_id, limit=None):
        return list(self.txs)

    def search(self, start_date=None, end_date=None, category_id=None, user_id=None, **_kwargs):
        results = []
        for tx in self.txs:
            if start_date and tx.occurred_at < start_date:
                continue
            if end_date and tx.occurred_at > end_date:
                continue
            if category_id and tx.category_id != category_id:
                continue
            results.append(tx)
        return results


class CategoryRepo:
    def __init__(self, cats):
        self.cats = cats

    def list_all(self, user_id):
        return list(self.cats)

    def get_by_id(self, cid, user_id):
        for c in self.cats:
            if c.id == cid:
                return c
        return None

    def upsert_by_slug(self, cat, user_id):
        cat.id = cat.id or len(self.cats) + 1
        self.cats.append(cat)
        return cat


class AccountRepo:
    def __init__(self, accounts):
        self.accounts = accounts

    def list_all(self, user_id):
        return list(self.accounts)

    def create(self, acct, user_id):
        acct.id = acct.id or len(self.accounts) + 1
        self.accounts.append(acct)
        return acct

    def get_by_id(self, account_id, user_id):
        for acct in self.accounts:
            if acct.id == account_id:
                return acct
        return None


class BudgetRepo:
    def __init__(self, budget, lines):
        self.budget = budget
        self.lines = lines

    def get_for_month(self, year, month, user_id):
        return self.budget

    def get_lines_for_budget(self, budget_id, user_id):
        return list(self.lines)

    def create_line(self, line, user_id):
        line.id = line.id or (max((l.id or 0 for l in self.lines), default=0) + 1)
        self.lines.append(line)
        return line

    def update_line(self, line, user_id):
        for idx, existing in enumerate(self.lines):
            if existing.id == line.id:
                self.lines[idx] = line
                return line
        self.lines.append(line)
        return line

    def delete_line(self, line_id, user_id):
        self.lines = [l for l in self.lines if l.id != line_id]
        return None


class HabitRepo:
    def __init__(self, items):
        self.items = items

    def list_active(self, user_id):
        return [h for h in self.items if h.is_active]

    def list_all(self, user_id, include_inactive=False):
        return list(self.items)

    def get_current_streak(self, hid, user_id):
        return 1

    def get_longest_streak(self, hid, user_id):
        return 2

    def get_entry(self, hid, occurred_on, user_id):
        return None

    def get_entries_for_habit(self, hid, start, end, user_id):
        return []

    def update(self, habit, user_id):
        return habit

    def get_by_id(self, hid, user_id):
        for h in self.items:
            if h.id == hid:
                return h
        return None

    def delete_entry(self, hid, occurred_on, user_id):
        return None

    def upsert_entry(self, entry, user_id):
        return entry


class HoldingRepo:
    def __init__(self, items):
        self.items = items

    def list_all(self, user_id):
        return list(self.items)

    def list_by_account(self, account_id, user_id):
        return [h for h in self.items if h.account_id == account_id]

    def get_total_cost_basis(self, user_id, account_id=None):
        holdings = self.list_by_account(account_id, user_id) if account_id else self.items
        return sum((h.quantity or 0) * (h.avg_price or 0) for h in holdings)

    def get_total_market_value(self, user_id, account_id=None):
        holdings = self.list_by_account(account_id, user_id) if account_id else self.items
        return sum((h.quantity or 0) * (h.market_price or h.avg_price or 0) for h in holdings)


def build_ctx(liabilities, txs, habits_list, holdings_list, budget, budget_lines):
    return types.SimpleNamespace(
        current_user=types.SimpleNamespace(id=1, role="user", username="tester"),
        current_month=date.today().replace(day=1),
        config=types.SimpleNamespace(DATA_DIR=Path(".")),
        liability_repo=LiabRepo(liabilities),
        transaction_repo=TxRepo(txs),
        category_repo=CategoryRepo(
            [
                Category(id=1, name="Food", slug="food", category_type="expense"),
                Category(id=2, name="Salary", slug="salary", category_type="income"),
            ]
        ),
        account_repo=AccountRepo([Account(id=1, name="Cash", currency="USD", user_id=1)]),
        budget_repo=BudgetRepo(budget, budget_lines),
        habit_repo=HabitRepo(habits_list),
        holding_repo=HoldingRepo(holdings_list),
        file_picker=None,
        budget_filter_start=None,
        budget_filter_end=None,
        budget_filter_quick_range="this_month",
        require_user_id=lambda: 1,
    )


@pytest.fixture(autouse=True)
def patch_ledger_service(monkeypatch):
    """Simplify ledger service helpers for deterministic action-button tests."""
    sample_txs = [
        Transaction(
            id=1,
            memo="Groceries",
            amount=-50.0,
            category_id=1,
            account_id=1,
            occurred_at=datetime(2024, 1, 1),
            user_id=1,
        ),
        Transaction(
            id=2,
            memo="Paycheck",
            amount=500.0,
            category_id=2,
            account_id=1,
            occurred_at=datetime(2024, 1, 2),
            user_id=1,
        ),
    ]

    monkeypatch.setattr(
        ledger_service,
        "filtered_transactions",
        lambda repo, filters: list(getattr(repo, "txs", sample_txs)),
    )
    monkeypatch.setattr(
        ledger_service,
        "paginate_transactions",
        lambda txs, pagination: (txs, pagination),
    )
    monkeypatch.setattr(
        ledger_service, "compute_summary", lambda txs: {"income": 0, "expenses": 0, "net": 0}
    )
    monkeypatch.setattr(ledger_service, "compute_spending_by_category", lambda txs, cats: [])
    monkeypatch.setattr(ledger_service, "top_categories", lambda breakdown, limit=5: breakdown)

    # Skip chart generation side-effects
    from pocketsage.desktop import charts

    monkeypatch.setattr(charts, "spending_chart_png", lambda *args, **kwargs: _tmp_png())
    monkeypatch.setattr(charts, "cashflow_by_account_png", lambda *args, **kwargs: _tmp_png())
    monkeypatch.setattr(charts, "category_trend_png", lambda *args, **kwargs: _tmp_png())
    monkeypatch.setattr(charts, "allocation_chart_png", lambda *args, **kwargs: _tmp_png())
    monkeypatch.setattr(charts, "debt_payoff_chart_png", lambda *args, **kwargs: _tmp_png())
    monkeypatch.setattr(charts, "cashflow_trend_png", lambda *args, **kwargs: _tmp_png())
    return sample_txs


def _assert_defaults(button, expected):
    captured = _captured_value(button.on_click)
    assert captured is not None, f"{button.tooltip} should capture target"
    assert captured == expected


def _captured_value(fn):
    defaults = getattr(fn, "__defaults__", None)
    if defaults and len(defaults) > 0:
        return defaults[0]
    closure = getattr(fn, "__closure__", None)
    if closure:
        for cell in closure:
            try:
                val = cell.cell_contents
                if not callable(val):
                    return val
            except Exception:
                continue
    return None


def test_action_buttons_capture_across_views(patch_ledger_service):
    liabilities = [
        Liability(id=1, name="Card A", balance=1000, apr=10, minimum_payment=25, user_id=1),
        Liability(id=2, name="Card B", balance=500, apr=15, minimum_payment=20, user_id=1),
    ]
    txs = patch_ledger_service
    habits_list = [
        Habit(id=1, name="Read", description="Read 10 pages", cadence="daily", user_id=1, is_active=True),
        Habit(id=2, name="Run", description="5k run", cadence="daily", user_id=1, is_active=True),
    ]
    holdings_list = [
        Holding(id=1, symbol="AAPL", quantity=1, avg_price=100, account_id=1, user_id=1),
        Holding(id=2, symbol="MSFT", quantity=2, avg_price=200, account_id=1, user_id=1),
    ]
    budget = Budget(
        id=1,
        period_start=date.today().replace(day=1),
        period_end=date.today(),
        label="Test Budget",
        user_id=1,
    )
    budget_lines = [
        BudgetLine(id=1, budget_id=1, category_id=1, planned_amount=100, rollover_enabled=False, user_id=1),
        BudgetLine(id=2, budget_id=1, category_id=2, planned_amount=200, rollover_enabled=False, user_id=1),
    ]

    ctx = build_ctx(liabilities, txs, habits_list, holdings_list, budget, budget_lines)

    # Debts
    debts_view = debts.build_debts_view(ctx, DummyPage())
    debts_table = _first_datatable(debts_view)
    assert debts_table and len(debts_table.rows) >= 2
    first_action_row = debts_table.rows[0].cells[-1].content.controls
    edit_btn, pay_btn, del_btn = first_action_row
    _assert_defaults(edit_btn, liabilities[0])
    _assert_defaults(pay_btn, liabilities[0])
    _assert_defaults(del_btn, liabilities[0].id)

    # Ledger
    ledger_page = DummyPage()
    ledger_view = ledger.build_ledger_view(ctx, ledger_page)
    # Trigger initial load via the filter "Apply" button (first FilledButton with filter icon)
    apply_buttons = [
        b for b in _collect_iconbuttons(ledger_view.controls, tooltip="Previous page")
    ]  # ensure controls traversed to warm recursion
    for ctrl in ledger_view.controls:
        pass
    apply_found = False
    stack = list(ledger_view.controls)
    while stack:
        ctrl = stack.pop()
        if isinstance(ctrl, ft.FilledButton) and getattr(ctrl, "icon", None) == ft.Icons.FILTER_ALT:
            ctrl.on_click(None)
            apply_found = True
            break
        for attr in ("controls", "content"):
            if hasattr(ctrl, attr):
                child = getattr(ctrl, attr)
                if isinstance(child, list):
                    stack.extend(child)
                elif child is not None:
                    stack.append(child)
    assert apply_found, "Apply button not found in ledger view"
    ledger_table = _first_datatable(ledger_view)
    assert ledger_table and len(ledger_table.rows) >= 2
    first_row = ledger_table.rows[0]
    assert callable(first_row.on_select_changed)
    first_row.on_select_changed(None)
    ledger_edit_btn = _find_button(ledger_view.controls, "Edit selected")
    ledger_del_btn = _find_button(ledger_view.controls, "Delete selected")
    assert ledger_edit_btn is not None and ledger_del_btn is not None
    assert ledger_edit_btn.disabled is False and ledger_del_btn.disabled is False

    # Habits
    habits_view = habits.build_habits_view(ctx, DummyPage())
    manage_edit = _find_button(habits_view.controls, "Edit selected")
    manage_archive = _find_button(habits_view.controls, "Archive selected")
    assert manage_edit is not None and manage_archive is not None
    # Click first habit card to select
    clickable = None
    stack = list(habits_view.controls)
    while stack and clickable is None:
        ctrl = stack.pop()
        if isinstance(ctrl, ft.Container) and getattr(ctrl, "on_click", None):
            clickable = ctrl
            break
        for attr in ("controls", "content"):
            if hasattr(ctrl, attr):
                child = getattr(ctrl, attr)
                if isinstance(child, list):
                    stack.extend(child)
                elif child is not None:
                    stack.append(child)
    assert clickable is not None
    clickable.on_click(None)
    assert manage_edit.disabled is False and manage_archive.disabled is False

    # Portfolio
    portfolio_view = portfolio.build_portfolio_view(ctx, DummyPage())
    portfolio_table = _first_datatable(portfolio_view)
    assert portfolio_table and len(portfolio_table.rows) >= 2
    first_holding_row = portfolio_table.rows[0]
    assert callable(first_holding_row.on_select_changed)
    first_holding_row.on_select_changed(None)
    port_edit_btn = _find_button(portfolio_view.controls, "Edit selected")
    port_del_btn = _find_button(portfolio_view.controls, "Delete selected")
    assert port_edit_btn is not None and port_del_btn is not None
    assert port_edit_btn.disabled is False and port_del_btn.disabled is False

    # Budgets
    budgets_view = budgets.build_budgets_view(ctx, DummyPage())
    assert budgets_view is not None

"""Ledger view implementation with guest-mode CRUD, filters, and budget snapshot."""

from __future__ import annotations

import math
import re
from calendar import monthrange
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from ...devtools import dev_log
from ...models.account import Account
from ...models.category import Category
from ...models.transaction import Transaction
from ...services.export_csv import export_transactions_csv
from .. import controllers
from ..charts import spending_chart_png
from ..components import build_app_bar, build_main_layout, build_progress_bar
from ..components.dialogs import show_confirm_dialog, show_error_dialog

if TYPE_CHECKING:
    from ..context import AppContext


_SLUG_PATTERN = re.compile(r"[^a-z0-9]+")


def _slugify(label: str) -> str:
    cleaned = _SLUG_PATTERN.sub("-", (label or "").strip().lower())
    cleaned = cleaned.strip("-")
    return cleaned or "uncategorized"


def build_ledger_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the ledger view with filters, pagination, category management, and budget snapshot."""

    uid = ctx.require_user_id()
    per_page = 25
    current_page = 1
    total_pages = 1
    filtered: list[Transaction] = []

    start_field = ft.TextField(label="Start date", hint_text="YYYY-MM-DD", width=140)
    end_field = ft.TextField(label="End date", hint_text="YYYY-MM-DD", width=140)
    type_field = ft.Dropdown(
        label="Type",
        options=[
            ft.dropdown.Option("all", "All"),
            ft.dropdown.Option("income", "Income"),
            ft.dropdown.Option("expense", "Expense"),
        ],
        value="all",
        width=140,
    )
    category_field = ft.Dropdown(label="Category", value="", width=200)
    search_field = ft.TextField(label="Search", hint_text="memo contains...", width=200)

    table_ref = ft.Ref[ft.DataTable]()
    income_text = ft.Ref[ft.Text]()
    expense_text = ft.Ref[ft.Text]()
    net_text = ft.Ref[ft.Text]()
    page_label = ft.Ref[ft.Text]()
    budget_progress_ref = ft.Ref[ft.Column]()
    category_list_ref = ft.Ref[ft.Column]()
    spending_image_ref = ft.Ref[ft.Image]()

    editing_category_id: int | None = None

    def _refresh_category_filter(selected: str = "") -> list[Category]:
        current_categories = ctx.category_repo.list_all(user_id=uid)
        category_field.options = [ft.dropdown.Option("", "All")] + [
            ft.dropdown.Option(str(c.id), c.name) for c in current_categories
        ]
        category_field.value = selected
        if category_field.page:
            category_field.update()
        return current_categories

    def _ensure_default_categories():
        defaults = [
            ("Income", "income"),
            ("Salary", "income"),
            ("Bonus", "income"),
            ("Groceries", "expense"),
            ("Dining Out", "expense"),
            ("Transport", "expense"),
            ("Utilities", "expense"),
            ("Rent/Mortgage", "expense"),
            ("Entertainment", "expense"),
            ("Health", "expense"),
        ]
        for name, ctype in defaults:
            slug = _slugify(name)
            if ctx.category_repo.get_by_slug(slug, user_id=uid):
                continue
            ctx.category_repo.create(
                Category(name=name, slug=slug, category_type=ctype, user_id=uid),
                user_id=uid,
            )

    _ensure_default_categories()
    _refresh_category_filter("")

    def parse_date(raw: str):
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    def update_table():
        nonlocal current_page, total_pages
        start_idx = (current_page - 1) * per_page
        subset = filtered[start_idx : start_idx + per_page]
        rows: list[ft.DataRow] = []
        for tx in subset:
            cat_name = ""
            if tx.category_id:
                cat = ctx.category_repo.get_by_id(tx.category_id, user_id=uid)
                cat_name = cat.name if cat else ""
            rows.append(
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(tx.occurred_at.strftime("%Y-%m-%d"))),
                        ft.DataCell(ft.Text(tx.memo)),
                        ft.DataCell(ft.Text(cat_name)),
                        ft.DataCell(ft.Text("Income" if tx.amount >= 0 else "Expense")),
                        ft.DataCell(
                            ft.Text(
                                f"${tx.amount:,.2f}",
                                color=ft.Colors.GREEN if tx.amount >= 0 else ft.Colors.RED,
                            )
                        ),
                        ft.DataCell(ft.Text(tx.currency)),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Edit",
                                        on_click=lambda _, item=tx: open_transaction_dialog(item),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        tooltip="Delete",
                                        icon_color=ft.Colors.RED,
                                        on_click=lambda _, tx_id=tx.id: delete_transaction(tx_id),
                                    ),
                                ]
                            )
                        ),
                    ]
                )
            )
        table = table_ref.current
        if table:
            if rows:
                table.rows = rows
            else:
                table.rows = [
                    ft.DataRow(
                        cells=[ft.DataCell(ft.Text("No transactions found")) for _ in range(7)]
                    )
                ]
        page_label.current.value = f"Page {current_page} / {total_pages}"
        page.update()

    def refresh_month_summary():
        month_start = ctx.current_month.replace(day=1)
        summary = ctx.transaction_repo.get_monthly_summary(
            month_start.year, month_start.month, user_id=uid
        )
        if income_text.current:
            income_text.current.value = f"${summary['income']:,.2f}"
        if expense_text.current:
            expense_text.current.value = f"${summary['expenses']:,.2f}"
        if net_text.current:
            net_text.current.value = f"${summary['net']:,.2f}"
        page.update()

    def refresh_budget_progress():
        month_start = ctx.current_month.replace(day=1)
        last_day = monthrange(month_start.year, month_start.month)[1]
        month_end = month_start.replace(day=last_day)
        budget = ctx.budget_repo.get_for_month(month_start.year, month_start.month, user_id=uid)
        container = budget_progress_ref.current
        if not container:
            return
        rows: list[ft.Control] = []
        if not budget:
            rows.append(ft.Text("No budget set for this month", color=ft.Colors.ON_SURFACE_VARIANT))
        else:
            lines = ctx.budget_repo.get_lines_for_budget(budget.id, user_id=uid)
            total_planned = sum(line.planned_amount for line in lines)
            total_spent = 0.0
            rows.append(
                ft.Text(
                    f"{month_start.strftime('%B %Y')} budget progress",
                    weight=ft.FontWeight.BOLD,
                )
            )
            for line in lines:
                category = ctx.category_repo.get_by_id(line.category_id, user_id=uid)
                txs = ctx.transaction_repo.search(
                    start_date=month_start,
                    end_date=month_end,
                    category_id=line.category_id,
                    user_id=uid,
                )
                actual = sum(abs(t.amount) for t in txs if t.amount < 0)
                total_spent += actual
                rows.append(
                    build_progress_bar(
                        current=actual,
                        maximum=line.planned_amount or 0.01,
                        label=category.name if category else "Uncategorized",
                    )
                )
            if total_planned > 0:
                rows.insert(
                    1,
                    build_progress_bar(
                        current=total_spent,
                        maximum=total_planned,
                        label="Overall budget",
                    ),
                )
        container.controls = rows
        if getattr(container, "page", None):
            container.update()

    def refresh_spending_chart():
        """Render a spending chart for the current month."""
        try:
            month_start = ctx.current_month.replace(day=1)
            last_day = monthrange(month_start.year, month_start.month)[1]
            month_end = month_start.replace(day=last_day)
            txs = ctx.transaction_repo.search(
                start_date=month_start,
                end_date=month_end,
                user_id=uid,
            )
            categories = ctx.category_repo.list_all(user_id=uid)
            cat_lookup = {c.id: c.name for c in categories if c.id is not None}
            path = spending_chart_png(txs, category_lookup=cat_lookup)
            if spending_image_ref.current:
                spending_image_ref.current.src = path.as_posix()
                spending_image_ref.current.visible = True
                if getattr(spending_image_ref.current, "page", None):
                    spending_image_ref.current.update()
        except Exception as exc:
            dev_log(ctx.config, "Spending chart refresh failed", exc=exc)
            if spending_image_ref.current:
                spending_image_ref.current.visible = False
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Saved, but spending chart failed to render"),
                show_close_icon=True,
            )
            page.snack_bar.open = True

    def apply_filters(page_index: int = 1):
        nonlocal filtered, current_page, total_pages
        start_dt = parse_date(start_field.value or "")
        end_dt = parse_date(end_field.value or "")
        raw_category = (category_field.value or "").strip()
        try:
            category_id = int(raw_category) if raw_category else None
        except ValueError:
            category_id = None
        txs = ctx.transaction_repo.search(
            start_date=start_dt,
            end_date=end_dt,
            category_id=category_id,
            text=(search_field.value or "").strip() or None,
            user_id=uid,
        )
        t_filter = type_field.value
        if t_filter == "income":
            txs = [t for t in txs if t.amount >= 0]
        elif t_filter == "expense":
            txs = [t for t in txs if t.amount < 0]

        txs = sorted(txs, key=lambda t: t.occurred_at, reverse=True)
        filtered = txs
        total_pages = max(1, math.ceil(len(txs) / per_page))
        current_page = max(1, min(page_index, total_pages))
        update_table()
        refresh_month_summary()
        refresh_budget_progress()
        refresh_spending_chart()

    def reset_filters(_):
        start_field.value = ""
        end_field.value = ""
        category_field.value = ""
        search_field.value = ""
        type_field.value = "all"
        apply_filters(1)

    def paginate(delta: int):
        target = current_page + delta
        target = max(1, min(target, total_pages))
        apply_filters(target)

    def _ensure_default_account():
        accounts = ctx.account_repo.list_all(user_id=uid)
        if accounts:
            return accounts
        default_account = ctx.account_repo.create(
            Account(name="Cash", currency="USD", user_id=uid), user_id=uid
        )
        return [default_account]

    def open_transaction_dialog(tx: Transaction | None = None):
        categories = ctx.category_repo.list_all(user_id=uid)
        if not categories:
            default_cat = ctx.category_repo.create(
                Category(
                    name="General",
                    slug="general",
                    category_type="expense",
                    user_id=uid,
                ),
                user_id=uid,
            )
            categories = [default_cat]

        accounts = _ensure_default_account()

        is_edit = tx is not None
        amount = ft.TextField(
            label="Amount",
            width=200,
            helper_text="Positive for income, negative for expenses.",
            value=str(abs(tx.amount)) if tx else "",
        )
        memo = ft.TextField(
            label="Memo",
            expand=True,
            helper_text="What was this transaction for?",
            value=tx.memo if tx else "",
        )
        date_field = ft.TextField(
            label="Date",
            value=(
                tx.occurred_at.strftime("%Y-%m-%d")
                if tx
                else datetime.now().strftime("%Y-%m-%d")
            ),
            width=200,
        )
        type_toggle = ft.RadioGroup(
            value="income" if tx and tx.amount >= 0 else "expense",
            content=ft.Row(
                [
                    ft.Radio(value="income", label="Income"),
                    ft.Radio(value="expense", label="Expense"),
                ],
                spacing=12,
            ),
        )
        category_dd = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(str(c.id), c.name) for c in categories],
            width=220,
            value=str(tx.category_id) if tx and tx.category_id else None,
        )
        account_dd = ft.Dropdown(
            label="Account",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in accounts],
            width=200,
            value=str(tx.account_id) if tx and tx.account_id else None,
        )

        def _set_error(control: ft.TextField, message: str | None):
            control.error_text = message
            if getattr(control, "page", None):
                control.update()

        def save_txn(_):
            warning_msg: str | None = None
            try:
                _set_error(amount, None)
                _set_error(memo, None)
                _set_error(date_field, None)
                occurred_at = datetime.fromisoformat((date_field.value or "").strip())
                amt_val = float(amount.value or 0)
                if type_toggle.value == "expense" and amt_val > 0:
                    amt_val = -amt_val
                if type_toggle.value == "income" and amt_val < 0:
                    amt_val = abs(amt_val)
                if amt_val == 0:
                    _set_error(amount, "Amount cannot be zero")
                    raise ValueError("Amount cannot be zero")
                if not memo.value:
                    _set_error(memo, "Description is required")
                    raise ValueError("Memo is required")
                cat_id_val = int(category_dd.value) if category_dd.value else None
                # Budget overrun check for expenses
                if amt_val < 0:
                    month_start = ctx.current_month.replace(day=1)
                    last_day = monthrange(month_start.year, month_start.month)[1]
                    month_end = month_start.replace(day=last_day)
                    budget = ctx.budget_repo.get_for_month(
                        month_start.year, month_start.month, user_id=uid
                    )
                    delta = abs(amt_val)
                    if is_edit and tx and tx.amount < 0:
                        delta = max(0.0, abs(amt_val) - abs(tx.amount))
                    if budget and delta > 0:
                        lines = ctx.budget_repo.get_lines_for_budget(budget.id, user_id=uid)
                        line = next((l for l in lines if l.category_id == cat_id_val), None)
                        if line:
                            txs = ctx.transaction_repo.search(
                                start_date=month_start,
                                end_date=month_end,
                                category_id=line.category_id,
                                user_id=uid,
                            )
                            actual = sum(
                                abs(t.amount)
                                for t in txs
                                if t.amount < 0 and (not is_edit or not tx or t.id != tx.id)
                            )
                            projected = actual + delta
                            if projected > line.planned_amount:
                                over_by = projected - line.planned_amount
                                category_name = next(
                                    (c.name for c in categories if c.id == cat_id_val),
                                    "Category",
                                )
                                warning_msg = (
                                    f"{category_name} budget exceeded by ${over_by:,.2f}"
                                )
                        elif lines:
                            total_planned = sum(l.planned_amount for l in lines)
                            txs = ctx.transaction_repo.search(
                                start_date=month_start,
                                end_date=month_end,
                                user_id=uid,
                            )
                            actual_total = sum(
                                abs(t.amount)
                                for t in txs
                                if t.amount < 0 and (not is_edit or not tx or t.id != tx.id)
                            )
                            projected_total = actual_total + delta
                            if projected_total > total_planned:
                                warning_msg = f"Overall budget exceeded by ${projected_total - total_planned:,.2f}"
            except ValueError as exc:
                dev_log(ctx.config, "Ledger validation failed", exc=exc)
                show_error_dialog(page, "Validation failed", str(exc))
                return
            except Exception as exc:
                dev_log(ctx.config, "Ledger parse failed", exc=exc)
                show_error_dialog(page, "Invalid input", str(exc))
                return

            try:
                if is_edit and tx:
                    tx.amount = amt_val
                    tx.memo = memo.value or ""
                    tx.occurred_at = occurred_at
                    tx.category_id = int(category_dd.value) if category_dd.value else None
                    tx.account_id = int(account_dd.value) if account_dd.value else None
                    tx.currency = tx.currency or "USD"
                    ctx.transaction_repo.update(tx, user_id=uid)
                else:
                    txn = Transaction(
                        amount=amt_val,
                        memo=memo.value or "",
                        occurred_at=occurred_at,
                        category_id=int(category_dd.value) if category_dd.value else None,
                        account_id=int(account_dd.value) if account_dd.value else None,
                        currency="USD",
                    )
                    ctx.transaction_repo.create(txn, user_id=uid)
                dlg.open = False
                apply_filters(current_page)
                msg = (
                    f"Transaction {'updated' if is_edit else 'saved'} "
                    f"({ 'income' if amt_val >= 0 else 'expense'} ${abs(amt_val):,.2f})"
                )
                if warning_msg:
                    msg = f"{msg} — {warning_msg}"
                page.snack_bar = ft.SnackBar(content=ft.Text(msg))
                page.snack_bar.open = True
                page.update()
            except Exception as exc:
                dev_log(ctx.config, "Ledger save failed", exc=exc)
                show_error_dialog(page, "Save failed", str(exc))

        dlg = ft.AlertDialog(
            title=ft.Text("Edit transaction" if is_edit else "Add transaction"),
            content=ft.Column(
                [
                    ft.Text(
                        "Expenses will be saved as negatives; switch to Income for inflows.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    amount,
                    type_toggle,
                    memo,
                    date_field,
                    category_dd,
                    account_dd,
                ],
                tight=True,
                spacing=8,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(dlg, "open", False)),
                ft.FilledButton("Save", on_click=save_txn),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    def delete_transaction(txn_id: int | None):
        if txn_id is None:
            return

        def confirm():
            try:
                ctx.transaction_repo.delete(txn_id, user_id=uid)
                dev_log(ctx.config, "Transaction deleted", context={"id": txn_id})
                apply_filters(current_page)
            except Exception as exc:
                dev_log(ctx.config, "Delete failed", exc=exc, context={"id": txn_id})
                show_error_dialog(page, "Delete failed", str(exc))

        show_confirm_dialog(page, "Delete transaction", "Are you sure?", confirm)

    def _write_export(path: Path):
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            export_transactions_csv(transactions=filtered, output_path=path)
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Exported to {path}"), show_close_icon=True
            )
            page.snack_bar.open = True
            page.update()
        except Exception as exc:
            show_error_dialog(page, "Export failed", str(exc))

    def export_csv(_):
        stamp = datetime.now().strftime("%Y%m%d%H%M%S")
        suggested = f"ledger_export_{stamp}.csv"
        dev_log(ctx.config, "Starting ledger export", context={"suggested": suggested})
        controllers.pick_export_destination(
            ctx,
            page,
            suggested_name=suggested,
            on_path_selected=_write_export,
        )

    filter_bar = ft.Row(
        [
            start_field,
            end_field,
            type_field,
            category_field,
            search_field,
            ft.FilledButton("Apply", icon=ft.Icons.FILTER_ALT, on_click=lambda _: apply_filters(1)),
            ft.TextButton("Reset", on_click=reset_filters),
        ],
        run_spacing=8,
        spacing=8,
        wrap=True,
    )

    summary_cards = ft.Row(
        [
            ft.Card(
                content=ft.Container(
                    ft.Column(
                        [
                            ft.Text("Income (this month)"),
                            ft.Text("", ref=income_text, size=20, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    padding=12,
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    ft.Column(
                        [
                            ft.Text("Expenses (this month)"),
                            ft.Text("", ref=expense_text, size=20, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    padding=12,
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    ft.Column(
                        [
                            ft.Text("Net (this month)"),
                            ft.Text("", ref=net_text, size=20, weight=ft.FontWeight.BOLD),
                        ]
                    ),
                    padding=12,
                ),
                expand=True,
            ),
        ],
        spacing=12,
    )

    spending_chart_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Spending breakdown (this month)", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Expenses by category (colorblind-friendly palette).",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Image(ref=spending_image_ref, height=280, fit=ft.ImageFit.CONTAIN),
                ],
                spacing=8,
            ),
            padding=16,
        ),
        elevation=2,
    )

    table = ft.DataTable(
        ref=table_ref,
        columns=[
            ft.DataColumn(ft.Text("Date")),
            ft.DataColumn(ft.Text("Description")),
            ft.DataColumn(ft.Text("Category")),
            ft.DataColumn(ft.Text("Type")),
            ft.DataColumn(ft.Text("Amount")),
            ft.DataColumn(ft.Text("Currency")),
            ft.DataColumn(ft.Text("Actions")),
        ],
        rows=[],
        expand=True,
    )

    pagination = ft.Row(
        [
            ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=lambda _: paginate(-1)),
            ft.Text("", ref=page_label),
            ft.IconButton(icon=ft.Icons.ARROW_FORWARD, on_click=lambda _: paginate(1)),
            ft.FilledButton(
                "Add transaction",
                icon=ft.Icons.ADD,
                on_click=lambda _: open_transaction_dialog(None),
            ),
            ft.TextButton(
                "Import CSV", on_click=lambda _: controllers.start_ledger_import(ctx, page)
            ),
            ft.TextButton("Export CSV", on_click=export_csv),
            ft.TextButton("CSV Help", on_click=lambda _: controllers.go_to_help(page)),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    category_name_field = ft.TextField(label="Category name", width=220)
    category_type_field = ft.Dropdown(
        label="Type",
        options=[
            ft.dropdown.Option("expense", "Expense"),
            ft.dropdown.Option("income", "Income"),
        ],
        value="expense",
        width=160,
    )

    def _reset_category_form():
        nonlocal editing_category_id
        editing_category_id = None
        category_name_field.value = ""
        category_type_field.value = "expense"
        category_name_field.error_text = None
        category_name_field.update()
        category_type_field.update()

    def _start_edit_category(cat: Category):
        nonlocal editing_category_id
        editing_category_id = cat.id
        category_name_field.value = cat.name
        category_type_field.value = cat.category_type
        category_name_field.update()
        category_type_field.update()

    def _render_category_list():
        container = category_list_ref.current
        if not container:
            return
        cats = ctx.category_repo.list_all(user_id=uid)
        items: list[ft.Control] = []
        for cat in cats:
            items.append(
                ft.Row(
                    [
                        ft.Text(cat.name, weight=ft.FontWeight.BOLD),
                        ft.Chip(label=ft.Text(cat.category_type.capitalize())),
                        ft.IconButton(
                            icon=ft.Icons.EDIT,
                            tooltip="Edit",
                            on_click=lambda _, c=cat: _start_edit_category(c),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE_OUTLINE,
                            icon_color=ft.Colors.RED,
                            tooltip="Delete",
                            on_click=lambda _, cid=cat.id: _delete_category(cid),
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                )
            )
        if not items:
            items.append(ft.Text("No categories yet. Add one to get started."))
        container.controls = items
        if getattr(container, "page", None):
            container.update()
        _refresh_category_filter(category_field.value or "")

    def _save_category(_):
        name = (category_name_field.value or "").strip()
        if not name:
            category_name_field.error_text = "Name is required"
            category_name_field.update()
            return
        category_name_field.error_text = None
        slug = _slugify(name)
        try:
            if editing_category_id:
                existing = ctx.category_repo.get_by_id(editing_category_id, user_id=uid)
                if not existing:
                    raise ValueError("Category not found")
                existing.name = name
                existing.slug = slug
                existing.category_type = category_type_field.value or "expense"
                ctx.category_repo.update(existing, user_id=uid)
            else:
                ctx.category_repo.upsert_by_slug(
                    Category(
                        name=name,
                        slug=slug,
                        category_type=category_type_field.value or "expense",
                        user_id=uid,
                    ),
                    user_id=uid,
                )
            _reset_category_form()
            _render_category_list()
            apply_filters(current_page)
        except Exception as exc:
            show_error_dialog(page, "Category save failed", str(exc))

    def _delete_category(cat_id: int | None):
        if not cat_id:
            return

        def _confirm_delete():
            try:
                ctx.category_repo.delete(cat_id, user_id=uid)
                _render_category_list()
                apply_filters(current_page)
            except Exception as exc:
                show_error_dialog(page, "Delete failed", str(exc))

        show_confirm_dialog(page, "Delete category", "Remove this category?", _confirm_delete)

    category_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Categories", size=18, weight=ft.FontWeight.BOLD),
                    ft.Row([category_name_field, category_type_field], spacing=12),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Save category",
                                icon=ft.Icons.SAVE,
                                on_click=_save_category,
                            ),
                            ft.TextButton("Cancel", on_click=lambda _: _reset_category_form()),
                        ],
                        spacing=8,
                    ),
                    ft.Divider(),
                    ft.Column(ref=category_list_ref, spacing=6),
                ],
                spacing=10,
            ),
            padding=16,
        ),
        elevation=2,
    )

    budget_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Budget progress", size=18, weight=ft.FontWeight.BOLD),
                    ft.Column(ref=budget_progress_ref, spacing=10),
                ],
                spacing=10,
            ),
            padding=16,
        ),
        elevation=2,
    )

    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Ledger", size=24, weight=ft.FontWeight.BOLD),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(height=12),
            filter_bar,
            ft.Container(height=12),
            summary_cards,
            ft.Container(height=12),
            spending_chart_section,
            ft.Container(height=12),
            budget_section,
            ft.Container(height=12),
            category_section,
            ft.Container(height=12),
            ft.Card(content=ft.Container(content=table, padding=12), expand=True),
            pagination,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    _render_category_list()
    refresh_month_summary()
    refresh_budget_progress()
    apply_filters()

    app_bar = build_app_bar(ctx, "Ledger", page)
    main_layout = build_main_layout(ctx, page, "/ledger", content)

    return ft.View(route="/ledger", appbar=app_bar, controls=main_layout, padding=0)

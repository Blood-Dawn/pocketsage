"""Ledger view implementation."""

# TODO(@codex): Ledger MVP features to implement/enhance:
#    - Transaction CRUD with filtering by date and category (DONE)
#    - Categories management UI (add/edit categories)
#    - Budget tracking display (show current vs budgeted amounts with progress bars)
#    - Monthly summaries (income vs expense for current month) (DONE - basic)
#    - Spending chart (pie/bar chart of expenses by category)
#    - CSV import/export (DONE - export implemented, import needs idempotency)
#    - Form validation with clear error messages (DONE - basic)

from __future__ import annotations

import math
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from ...models.transaction import Transaction
from ...models.account import Account
from ...models.category import Category
from ...services.export_csv import export_transactions_csv
from ...devtools import dev_log
from .. import controllers
from ..components import build_app_bar, build_main_layout
from ..components.dialogs import show_confirm_dialog, show_error_dialog

if TYPE_CHECKING:
    from ..context import AppContext


def build_ledger_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the ledger view with filters, pagination, and quick add."""

    uid = ctx.require_user_id()
    per_page = 25
    current_page = 1
    total_pages = 1
    filtered: list[Transaction] = []

    categories = ctx.category_repo.list_all(user_id=uid)

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
    category_field = ft.Dropdown(
        label="Category",
        options=[ft.dropdown.Option("", "All")]
        + [ft.dropdown.Option(str(c.id), c.name) for c in categories],
        value="",
        width=200,
    )
    search_field = ft.TextField(label="Search", hint_text="memo contains...", width=200)

    table_ref = ft.Ref[ft.DataTable]()
    income_text = ft.Ref[ft.Text]()
    expense_text = ft.Ref[ft.Text]()
    net_text = ft.Ref[ft.Text]()
    page_label = ft.Ref[ft.Text]()

    def parse_date(raw: str):
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    def apply_filters(page_index: int = 1):
        nonlocal filtered, current_page, total_pages
        start_dt = parse_date(start_field.value or "")
        end_dt = parse_date(end_field.value or "")
        # TODO(@codex): Fix category filter to handle "All" selection properly
        #    - When "All" is selected, category_field.value is empty string ""
        #    - Must not attempt int conversion on empty string (prevents ValueError)
        #    - Only convert to int if value isdigit() check passes
        raw_category = (category_field.value or "").strip()
        category_id = int(raw_category) if raw_category.isdigit() else None
        txs = ctx.transaction_repo.search(
            start_date=start_dt,
            end_date=end_dt,
            category_id=category_id,
            text=(search_field.value or "").strip() or None,
            user_id=uid,
        )
        # type filter
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
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        tooltip="Delete",
                                        icon_color=ft.Colors.RED,
                                        on_click=lambda _, tx_id=tx.id: delete_transaction(tx_id),
                                    )
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
        # summary
        income = sum(t.amount for t in filtered if t.amount >= 0)
        expenses = sum(abs(t.amount) for t in filtered if t.amount < 0)
        net = income - expenses
        income_text.current.value = f"${income:,.2f}"
        expense_text.current.value = f"${expenses:,.2f}"
        net_text.current.value = f"${net:,.2f}"
        page_label.current.value = f"Page {current_page} / {total_pages}"
        page.update()

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

    # TODO(@codex): Add transaction dialog with form validation
    #    - Validate that amount is a number (DONE)
    #    - Validate that date is valid (DONE)
    #    - Ensure memo is not empty (DONE)
    #    - Show clear error messages on invalid input (DONE via show_error_dialog)
    #    - This addresses FR-8 (validation) and NFR-17 (error messages)
    def add_transaction_dialog(_):
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

        accounts = ctx.account_repo.list_all(user_id=uid)
        if not accounts:
            default_account = ctx.account_repo.create(
                Account(name="Cash", currency="USD", user_id=uid), user_id=uid
            )
            accounts = [default_account]

        amount = ft.TextField(
            label="Amount",
            width=200,
            helper_text="Enter amount; positive for income, negative for expenses.",
        )
        memo = ft.TextField(label="Memo", expand=True, helper_text="What was this transaction for?")
        date_field = ft.TextField(
            label="Date", value=datetime.now().strftime("%Y-%m-%d"), width=200
        )
        type_toggle = ft.RadioGroup(
            value="expense",
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
            width=200,
        )
        account_dd = ft.Dropdown(
            label="Account",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in accounts],
            width=200,
        )

        def save_txn(_):
            try:
                occurred_at = datetime.fromisoformat(date_field.value.strip())
                amt_val = float(amount.value or 0)
                if type_toggle.value == "expense" and amt_val > 0:
                    amt_val = -amt_val
                if type_toggle.value == "income" and amt_val < 0:
                    amt_val = abs(amt_val)
                if amt_val == 0:
                    raise ValueError("Amount cannot be zero")
                if not memo.value:
                    raise ValueError("Memo is required")
                txn = Transaction(
                    amount=amt_val,
                    memo=memo.value or "",
                    occurred_at=occurred_at,
                    category_id=int(category_dd.value) if category_dd.value else None,
                    account_id=int(account_dd.value) if account_dd.value else None,
                    currency="USD",
                )
                ctx.transaction_repo.create(txn, user_id=uid)
                dev_log(
                    ctx.config,
                    "Ledger transaction saved",
                    context={
                        "memo": txn.memo,
                        "amount": txn.amount,
                        "category_id": txn.category_id,
                    },
                )
                dlg.open = False
                apply_filters(current_page)
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(
                        f"Transaction saved ({'income' if amt_val >= 0 else 'expense'} ${abs(amt_val):,.2f})"
                    )
                )
                page.snack_bar.open = True
                page.update()
            except Exception as exc:
                dev_log(ctx.config, "Ledger save failed", exc=exc)
                show_error_dialog(page, "Save failed", str(exc))

        dlg = ft.AlertDialog(
            title=ft.Text("Add transaction"),
            content=ft.Column(
                [
                    ft.Text(
                        "Enter the transaction details. Expenses will be saved as negatives.",
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

    # TODO(@codex): Add budget tracking to summary cards
    #    - Display budget for current month (e.g., "Budget: $2000")
    #    - Show progress bar or percentage of budget used
    #    - Highlight when over budget (change color to red/warning)
    #    - This addresses FR-13 (budget thresholds) and UR-3 (monitor budgets)
    summary_cards = ft.Row(
        [
            ft.Card(
                content=ft.Container(
                    ft.Column(
                        [
                            ft.Text("Income"),
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
                            ft.Text("Expenses"),
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
                            ft.Text("Net"),
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
    # TODO(@codex): Embed spending chart (category breakdown)
    #    - Generate a pie or bar chart image of expenses by category for the month
    #    - Use Matplotlib to create the chart
    #    - Display the chart below summary cards
    #    - This addresses FR-11 (spending visualization) and UR-2 (view charts)

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
            ft.FilledButton("Add transaction", icon=ft.Icons.ADD, on_click=add_transaction_dialog),
            ft.TextButton(
                "Import CSV", on_click=lambda _: controllers.start_ledger_import(ctx, page)
            ),
            ft.TextButton("Export CSV", on_click=export_csv),
            ft.TextButton("CSV Help", on_click=lambda _: controllers.go_to_help(page)),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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
            ft.Card(content=ft.Container(content=table, padding=12), expand=True),
            pagination,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    apply_filters()

    app_bar = build_app_bar(ctx, "Ledger", page)
    main_layout = build_main_layout(ctx, page, "/ledger", content)

    return ft.View(route="/ledger", appbar=app_bar, controls=main_layout, padding=0)

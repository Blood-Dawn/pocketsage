"""Ledger view implementation."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING
import math

import flet as ft

from ...models.transaction import Transaction
from ...services.import_csv import ColumnMapping, import_csv_file
from ...services.export_csv import export_transactions_csv
from ..components import build_app_bar, build_main_layout
from ..components.dialogs import show_confirm_dialog, show_error_dialog

if TYPE_CHECKING:
    from ..context import AppContext


def build_ledger_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the ledger view with filters, pagination, and quick add."""

    per_page = 25
    current_page = 1
    total_pages = 1
    filtered: list[Transaction] = []

    categories = ctx.category_repo.list_all()
    accounts = ctx.account_repo.list_all()

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
        options=[ft.dropdown.Option("", "All")] + [ft.dropdown.Option(str(c.id), c.name) for c in categories],
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
        category_id = int(category_field.value) if category_field.value else None
        txs = ctx.transaction_repo.search(
            start_date=start_dt,
            end_date=end_dt,
            category_id=category_id,
            text=(search_field.value or "").strip() or None,
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
                cat = ctx.category_repo.get_by_id(tx.category_id)
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
                                color=ft.colors.GREEN if tx.amount >= 0 else ft.colors.RED,
                            )
                        ),
                        ft.DataCell(ft.Text(tx.currency)),
                        ft.DataCell(
                            ft.Row(
                                [
                                    ft.IconButton(
                                        icon=ft.icons.DELETE_OUTLINE,
                                        tooltip="Delete",
                                        icon_color=ft.colors.RED,
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
                    ft.DataRow(cells=[ft.DataCell(ft.Text("No transactions found")) for _ in range(7)])
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

    def add_transaction_dialog(_):
        categories = ctx.category_repo.list_all()
        accounts = ctx.account_repo.list_all()
        amount = ft.TextField(label="Amount", width=200)
        memo = ft.TextField(label="Memo", expand=True)
        date_field = ft.TextField(label="Date", value=datetime.now().strftime("%Y-%m-%d"), width=200)
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
                occurred_at = datetime.fromisoformat(date_field.value)
                txn = Transaction(
                    amount=float(amount.value or 0),
                    memo=memo.value or "",
                    occurred_at=occurred_at,
                    category_id=int(category_dd.value) if category_dd.value else None,
                    account_id=int(account_dd.value) if account_dd.value else None,
                    currency="USD",
                )
                ctx.transaction_repo.create(txn)
                dlg.open = False
                apply_filters(current_page)
                page.snack_bar = ft.SnackBar(content=ft.Text("Transaction saved"))
                page.snack_bar.open = True
                page.update()
            except Exception as exc:
                show_error_dialog(page, "Save failed", str(exc))

        dlg = ft.AlertDialog(
            title=ft.Text("Add transaction"),
            content=ft.Column([amount, memo, date_field, category_dd, account_dd], tight=True, spacing=8),
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
                ctx.transaction_repo.delete(txn_id)
                apply_filters(current_page)
            except Exception as exc:
                show_error_dialog(page, "Delete failed", str(exc))

        show_confirm_dialog(page, "Delete transaction", "Are you sure?", confirm)

    def export_csv(_):
        try:
            from tempfile import NamedTemporaryFile

            with NamedTemporaryFile(delete=False, suffix=".csv") as tmp:
                export_transactions_csv(transactions=filtered, output_path=Path(tmp.name))
                page.snack_bar = ft.SnackBar(content=ft.Text(f"Exported to {tmp.name}"))
                page.snack_bar.open = True
                page.update()
        except Exception as exc:
            show_error_dialog(page, "Export failed", str(exc))

    def import_csv(_):
        # Simple text-path prompt to keep headless-safe; real UI would use FilePicker.
        path_field = ft.TextField(label="CSV path", width=320)

        def do_import(_):
            try:
                mapping = ColumnMapping(
                    amount="amount",
                    occurred_at="date",
                    memo="memo",
                    external_id="transaction_id",
                    category="category",
                    account_id="account",
                )
                count = import_csv_file(csv_path=Path(path_field.value), mapping=mapping)
                page.snack_bar = ft.SnackBar(content=ft.Text(f"Imported {count} rows"))
                page.snack_bar.open = True
                apply_filters(current_page)
            except Exception as exc:
                show_error_dialog(page, "Import failed", str(exc))
            dlg.open = False
            page.update()

        dlg = ft.AlertDialog(
            title=ft.Text("Import CSV"),
            content=path_field,
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: setattr(dlg, "open", False)),
                ft.FilledButton("Import", on_click=do_import),
            ],
        )
        page.dialog = dlg
        dlg.open = True
        page.update()

    filter_bar = ft.Row(
        [
            start_field,
            end_field,
            type_field,
            category_field,
            search_field,
            ft.FilledButton("Apply", icon=ft.icons.FILTER_ALT, on_click=lambda _: apply_filters(1)),
            ft.TextButton("Reset", on_click=reset_filters),
        ],
        run_spacing=8,
        spacing=8,
        wrap=True,
    )

    summary_cards = ft.Row(
        [
            ft.Card(content=ft.Container(ft.Column([ft.Text("Income"), ft.Text("", ref=income_text, size=20, weight=ft.FontWeight.BOLD)]), padding=12), expand=True),
            ft.Card(content=ft.Container(ft.Column([ft.Text("Expenses"), ft.Text("", ref=expense_text, size=20, weight=ft.FontWeight.BOLD)]), padding=12), expand=True),
            ft.Card(content=ft.Container(ft.Column([ft.Text("Net"), ft.Text("", ref=net_text, size=20, weight=ft.FontWeight.BOLD)]), padding=12), expand=True),
        ],
        spacing=12,
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
            ft.IconButton(icon=ft.icons.ARROW_BACK, on_click=lambda _: paginate(-1)),
            ft.Text("", ref=page_label),
            ft.IconButton(icon=ft.icons.ARROW_FORWARD, on_click=lambda _: paginate(1)),
            ft.FilledButton("Add transaction", icon=ft.icons.ADD, on_click=add_transaction_dialog),
            ft.TextButton("Import CSV", on_click=import_csv),
            ft.TextButton("Export CSV", on_click=export_csv),
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

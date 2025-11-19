"""Ledger view implementation."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import flet as ft

from ...models.transaction import Transaction
from ..components import build_app_bar, build_main_layout
from ..components.dialogs import show_confirm_dialog, show_error_dialog

if TYPE_CHECKING:
    from ..context import AppContext


def build_ledger_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the ledger view with transaction list and forms."""

    # State for form
    form_visible = ft.Ref[ft.Container]()
    txn_list_ref = ft.Ref[ft.Column]()

    # Form fields
    amount_field = ft.TextField(
        label="Amount",
        hint_text="Positive for income, negative for expense",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=200,
    )

    memo_field = ft.TextField(
        label="Description",
        hint_text="What was this transaction for?",
        expand=True,
    )

    # Get categories for dropdown
    categories = ctx.category_repo.list_all()
    category_dropdown = ft.Dropdown(
        label="Category",
        options=[
            ft.dropdown.Option(key=str(cat.id), text=cat.name)
            for cat in categories
        ],
        width=200,
    )

    # Get accounts for dropdown
    accounts = ctx.account_repo.list_all()
    account_dropdown = ft.Dropdown(
        label="Account",
        options=[
            ft.dropdown.Option(key=str(acc.id), text=acc.name)
            for acc in accounts
        ],
        width=200,
    )

    date_field = ft.TextField(
        label="Date",
        hint_text="YYYY-MM-DD",
        value=datetime.now().strftime("%Y-%m-%d"),
        width=200,
    )

    def refresh_transaction_list():
        """Refresh the transaction list."""
        transactions = ctx.transaction_repo.list_all(limit=50)
        rows = []

        for txn in transactions:
            amount_color = ft.colors.GREEN if txn.amount > 0 else ft.colors.RED
            category_name = ""
            if txn.category_id:
                cat = ctx.category_repo.get_by_id(txn.category_id)
                if cat:
                    category_name = cat.name

            rows.append(
                ft.Container(
                    content=ft.Row(
                        [
                            ft.Text(
                                txn.occurred_at.strftime("%Y-%m-%d"),
                                size=14,
                                width=100,
                            ),
                            ft.Text(
                                category_name,
                                size=14,
                                width=150,
                            ),
                            ft.Text(
                                txn.memo[:50] if len(txn.memo) > 50 else txn.memo,
                                size=14,
                                expand=True,
                            ),
                            ft.Text(
                                f"${abs(txn.amount):,.2f}",
                                size=14,
                                weight=ft.FontWeight.BOLD,
                                color=amount_color,
                                width=120,
                                text_align=ft.TextAlign.RIGHT,
                            ),
                            ft.IconButton(
                                icon=ft.icons.DELETE_OUTLINE,
                                icon_color=ft.colors.RED,
                                tooltip="Delete",
                                on_click=lambda e, txn_id=txn.id: delete_transaction(txn_id),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    padding=10,
                    border=ft.border.only(
                        bottom=ft.border.BorderSide(1, ft.colors.OUTLINE_VARIANT)
                    ),
                )
            )

        if not rows:
            rows.append(
                ft.Container(
                    content=ft.Text(
                        "No transactions yet. Add your first transaction above!",
                        color=ft.colors.ON_SURFACE_VARIANT,
                    ),
                    padding=20,
                )
            )

        txn_list_ref.current.controls = rows
        page.update()

    def toggle_form(e):
        """Toggle the add transaction form."""
        current = form_visible.current
        if current.visible:
            current.visible = False
        else:
            current.visible = True
        page.update()

    def add_transaction(e):
        """Add a new transaction."""
        try:
            # Validate and parse amount
            amount = float(amount_field.value or 0)

            # Parse date
            try:
                occurred_at = datetime.strptime(date_field.value, "%Y-%m-%d")
            except ValueError:
                occurred_at = datetime.now()

            # Create transaction
            txn = Transaction(
                amount=amount,
                memo=memo_field.value or "",
                occurred_at=occurred_at,
                category_id=int(category_dropdown.value) if category_dropdown.value else None,
                account_id=int(account_dropdown.value) if account_dropdown.value else None,
            )

            # Save
            ctx.transaction_repo.create(txn)

            # Clear form
            amount_field.value = ""
            memo_field.value = ""
            category_dropdown.value = None
            date_field.value = datetime.now().strftime("%Y-%m-%d")

            # Hide form
            form_visible.current.visible = False

            # Refresh list
            refresh_transaction_list()

            page.update()

        except Exception as ex:
            show_error_dialog(page, "Error", f"Failed to add transaction: {ex}")

    def delete_transaction(txn_id):
        """Delete a transaction."""

        def confirm_delete():
            try:
                ctx.transaction_repo.delete(txn_id)
                refresh_transaction_list()
            except Exception as ex:
                show_error_dialog(page, "Error", f"Failed to delete transaction: {ex}")

        show_confirm_dialog(
            page,
            "Delete Transaction",
            "Are you sure you want to delete this transaction?",
            on_confirm=confirm_delete,
        )

    # Add form
    add_form = ft.Container(
        ref=form_visible,
        visible=False,
        content=ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Add New Transaction", size=18, weight=ft.FontWeight.BOLD),
                        ft.Container(height=8),
                        ft.Row([date_field, account_dropdown], spacing=16),
                        ft.Row([amount_field, category_dropdown], spacing=16),
                        memo_field,
                        ft.Container(height=8),
                        ft.Row(
                            [
                                ft.FilledButton(
                                    "Add Transaction",
                                    icon=ft.icons.ADD,
                                    on_click=add_transaction,
                                ),
                                ft.TextButton(
                                    "Cancel",
                                    on_click=toggle_form,
                                ),
                            ],
                            spacing=8,
                        ),
                    ],
                ),
                padding=20,
            ),
        ),
        margin=ft.margin.only(bottom=16),
    )

    # Transaction list
    txn_list = ft.Column(ref=txn_list_ref, spacing=0, scroll=ft.ScrollMode.AUTO, expand=True)

    # Initialize list
    refresh_transaction_list()

    # Build content
    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Transactions", size=24, weight=ft.FontWeight.BOLD),
                    ft.FilledButton(
                        "Add Transaction",
                        icon=ft.icons.ADD,
                        on_click=toggle_form,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(height=16),
            add_form,
            ft.Card(
                content=ft.Column(
                    [
                        ft.Container(
                            content=ft.Row(
                                [
                                    ft.Text("Date", size=14, weight=ft.FontWeight.BOLD, width=100),
                                    ft.Text("Category", size=14, weight=ft.FontWeight.BOLD, width=150),
                                    ft.Text("Description", size=14, weight=ft.FontWeight.BOLD, expand=True),
                                    ft.Text("Amount", size=14, weight=ft.FontWeight.BOLD, width=120, text_align=ft.TextAlign.RIGHT),
                                    ft.Container(width=48),
                                ],
                            ),
                            padding=10,
                            bgcolor=ft.colors.SURFACE_VARIANT,
                        ),
                        txn_list,
                    ],
                    spacing=0,
                    expand=True,
                ),
                elevation=2,
            ),
        ],
        spacing=0,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Ledger")
    main_layout = build_main_layout(page, "/ledger", content)

    return ft.View(
        route="/ledger",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

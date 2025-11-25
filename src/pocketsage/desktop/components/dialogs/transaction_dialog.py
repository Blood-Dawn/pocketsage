"""Transaction add/edit dialogs.

Implements quick transaction add functionality:
- Create new transaction
- Edit existing transaction (future)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from ....logging_config import get_logger
from ....models.transaction import Transaction

if TYPE_CHECKING:
    from ...context import AppContext

logger = get_logger(__name__)


def show_transaction_dialog(
    ctx: AppContext,
    page: ft.Page,
    transaction: Transaction | None = None,
    on_save_callback=None,
) -> None:
    """Show create or edit transaction dialog.

    Args:
        ctx: Application context
        page: Flet page
        transaction: Existing transaction to edit, or None to create new
        on_save_callback: Optional callback function to call after successful save
    """
    is_edit = transaction is not None
    uid = ctx.require_user_id()

    # Load accounts and categories
    try:
        accounts = ctx.account_repo.list_all(user_id=uid)
        categories = ctx.category_repo.list_all(user_id=uid)
    except Exception as exc:
        logger.error(f"Failed to load accounts/categories: {exc}")
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Error loading data: {exc}"),
            bgcolor=ft.Colors.RED_400,
        )
        page.snack_bar.open = True
        page.update()
        return

    if not accounts:
        page.snack_bar = ft.SnackBar(
            content=ft.Text("Please create an account first (Settings > Accounts)"),
            bgcolor=ft.Colors.ORANGE_400,
        )
        page.snack_bar.open = True
        page.update()
        return

    # Form fields
    date_field = ft.TextField(
        label="Date *",
        value=str(transaction.date if transaction else date.today()),
        hint_text="YYYY-MM-DD",
        width=200,
    )

    description_field = ft.TextField(
        label="Description *",
        value=transaction.description if transaction else "",
        hint_text="e.g., Grocery shopping",
        autofocus=True,
        width=400,
    )

    amount_field = ft.TextField(
        label="Amount *",
        value=str(transaction.amount) if transaction else "",
        hint_text="0.00",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=150,
    )

    account_dropdown = ft.Dropdown(
        label="Account *",
        options=[ft.dropdown.Option(key=str(acc.id), text=acc.name) for acc in accounts],
        value=str(transaction.account_id) if transaction else (str(accounts[0].id) if accounts else None),
        width=250,
    )

    category_dropdown = ft.Dropdown(
        label="Category",
        options=[ft.dropdown.Option(key=str(cat.id), text=cat.name) for cat in categories],
        value=str(transaction.category_id) if transaction and transaction.category_id else None,
        width=250,
    )

    notes_field = ft.TextField(
        label="Notes (optional)",
        value=transaction.notes if transaction else "",
        multiline=True,
        min_lines=2,
        max_lines=4,
        width=400,
    )

    def _validate_and_save(_):
        """Validate form and save transaction."""
        # Clear previous errors
        date_field.error_text = None
        description_field.error_text = None
        amount_field.error_text = None
        account_dropdown.error_text = None

        # Validate date
        date_str = (date_field.value or "").strip()
        if not date_str:
            date_field.error_text = "Date is required"
            date_field.update()
            return

        try:
            txn_date = date.fromisoformat(date_str)
        except ValueError:
            date_field.error_text = "Invalid date format (use YYYY-MM-DD)"
            date_field.update()
            return

        # Validate description
        description = (description_field.value or "").strip()
        if not description:
            description_field.error_text = "Description is required"
            description_field.update()
            return

        # Validate amount
        amount_str = (amount_field.value or "").strip()
        if not amount_str:
            amount_field.error_text = "Amount is required"
            amount_field.update()
            return

        try:
            amount = Decimal(amount_str)
        except Exception:
            amount_field.error_text = "Invalid amount"
            amount_field.update()
            return

        # Validate account
        account_id_str = account_dropdown.value
        if not account_id_str:
            account_dropdown.error_text = "Account is required"
            account_dropdown.update()
            return

        try:
            account_id = int(account_id_str)
        except ValueError:
            account_dropdown.error_text = "Invalid account"
            account_dropdown.update()
            return

        # Optional category
        category_id = None
        if category_dropdown.value:
            try:
                category_id = int(category_dropdown.value)
            except ValueError:
                pass

        # Optional notes
        notes = (notes_field.value or "").strip() or None

        # Save transaction
        try:
            if is_edit:
                # Update existing
                transaction.date = txn_date
                transaction.description = description
                transaction.amount = amount
                transaction.account_id = account_id
                transaction.category_id = category_id
                transaction.notes = notes
                saved = ctx.ledger_repo.update(transaction)
                message = "Transaction updated successfully"
            else:
                # Create new
                new_txn = Transaction(
                    date=txn_date,
                    description=description,
                    amount=amount,
                    account_id=account_id,
                    category_id=category_id,
                    notes=notes,
                    user_id=uid,
                )
                saved = ctx.ledger_repo.create(new_txn)
                message = "Transaction added successfully"

            logger.info(f"Transaction saved: {saved.id}")

            # Show success
            page.snack_bar = ft.SnackBar(
                content=ft.Text(message),
                bgcolor=ft.Colors.GREEN_400,
            )
            page.snack_bar.open = True

            # Close dialog
            dialog.open = False
            page.update()

            # Call callback if provided
            if on_save_callback:
                on_save_callback()

        except Exception as exc:
            logger.error(f"Failed to save transaction: {exc}")
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error saving transaction: {exc}"),
                bgcolor=ft.Colors.RED_400,
            )
            page.snack_bar.open = True
            page.update()

    def _close_dialog(_):
        """Close dialog without saving."""
        dialog.open = False
        page.update()

    # Build dialog
    dialog = ft.AlertDialog(
        title=ft.Text("Edit Transaction" if is_edit else "New Transaction"),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    ft.Row([date_field, amount_field], spacing=10),
                    description_field,
                    ft.Row([account_dropdown, category_dropdown], spacing=10),
                    notes_field,
                ],
                tight=True,
                spacing=12,
            ),
            width=500,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close_dialog),
            ft.ElevatedButton(
                "Save" if not is_edit else "Update",
                icon=ft.Icons.SAVE,
                on_click=_validate_and_save,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    page.dialog = dialog
    dialog.open = True
    page.update()

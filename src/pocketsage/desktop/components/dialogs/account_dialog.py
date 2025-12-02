"""Account management dialogs.

Implements account CRUD functionality:
- Create new account
- Edit existing account
- List all accounts
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

import flet as ft

from ....logging_config import get_logger
from ....models.account import Account
from ...constants import ACCOUNT_TYPE_OPTIONS
from .. import safe_open_dialog

if TYPE_CHECKING:
    from ...context import AppContext

logger = get_logger(__name__)


def show_account_dialog(
    ctx: AppContext,
    page: ft.Page,
    account: Account | None = None,
    on_save_callback=None,
) -> None:
    """Show create or edit account dialog.

    Args:
        ctx: Application context
        page: Flet page
        account: Existing account to edit, or None to create new
        on_save_callback: Optional callback function to call after successful save
    """
    is_edit = account is not None
    uid = ctx.require_user_id()

    # Form fields
    name_field = ft.TextField(
        label="Account Name *",
        value=account.name if account else "",
        hint_text="e.g., Checking, Savings, Credit Card",
        autofocus=True,
        width=400,
    )

    account_type_dropdown = ft.Dropdown(
        label="Account Type *",
        value=account.account_type if account else "checking",
        options=[ft.dropdown.Option(key=key, text=text) for key, text in ACCOUNT_TYPE_OPTIONS],
        width=250,
    )
    if account and account.account_type and account.account_type not in {k for k, _ in ACCOUNT_TYPE_OPTIONS}:
        account_type_dropdown.options.append(
            ft.dropdown.Option(key=account.account_type, text=account.account_type.title())
        )

    balance_field = ft.TextField(
        label="Initial Balance",
        value=str(account.balance) if account else "0.00",
        hint_text="0.00",
        keyboard_type=ft.KeyboardType.NUMBER,
        width=150,
    )

    def _validate_and_save(_):
        """Validate form and save account."""
        # Clear previous errors
        name_field.error_text = None
        balance_field.error_text = None

        # Validate name
        name = (name_field.value or "").strip()
        if not name:
            name_field.error_text = "Name is required"
            name_field.update()
            return

        # Validate balance
        balance_str = (balance_field.value or "0").strip()
        try:
            balance = Decimal(balance_str)
        except Exception:
            balance_field.error_text = "Invalid balance"
            balance_field.update()
            return

        account_type = account_type_dropdown.value or "checking"

        # Save account
        try:
            if is_edit:
                # Update existing
                account.name = name
                account.account_type = account_type
                account.balance = balance
                saved = ctx.account_repo.update(account)
                message = "Account updated successfully"
            else:
                # Create new
                new_account = Account(
                    name=name,
                    account_type=account_type,
                    balance=balance,
                    user_id=uid,
                )
                saved = ctx.account_repo.create(new_account)
                message = "Account created successfully"

            logger.info(f"Account saved: {saved.id}")

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
            logger.error(f"Failed to save account: {exc}")
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error saving account: {exc}"),
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
        title=ft.Text("Edit Account" if is_edit else "New Account"),
        content=ft.Container(
            content=ft.Column(
                controls=[
                    name_field,
                    ft.Row([account_type_dropdown, balance_field], spacing=10),
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

    safe_open_dialog(page, dialog)


def show_account_list_dialog(ctx: AppContext, page: ft.Page) -> None:
    """Show list of accounts with edit/delete actions.

    Args:
        ctx: Application context
        page: Flet page
    """
    uid = ctx.require_user_id()

    def _refresh_list():
        """Refresh the account list."""
        try:
            accounts = ctx.account_repo.list_all(user_id=uid)
            account_list.controls.clear()

            if not accounts:
                account_list.controls.append(
                    ft.Container(
                        content=ft.Text("No accounts yet. Click 'New Account' to create one."),
                        padding=20,
                    )
                )
            else:
                for acc in accounts:
                    account_list.controls.append(
                        ft.ListTile(
                            leading=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET),
                            title=ft.Text(acc.name),
                            subtitle=ft.Text(f"{getattr(acc, 'account_type', 'checking').title()} - Balance: ${getattr(acc, 'balance', 0):,.2f}"),
                            trailing=ft.Row(
                                controls=[
                                    ft.IconButton(
                                        icon=ft.Icons.EDIT,
                                        tooltip="Edit",
                                        on_click=lambda _, a=acc: _edit_account(a),
                                    ),
                                    ft.IconButton(
                                        icon=ft.Icons.DELETE,
                                        tooltip="Delete",
                                        icon_color=ft.Colors.RED_400,
                                        on_click=lambda _, a=acc: _delete_account(a),
                                    ),
                                ],
                                spacing=0,
                            ),
                        )
                    )

            try:
                account_list.update()
            except AssertionError:
                # Dialog/tests may not attach the list to a page; ignore in that case.
                pass
        except Exception as exc:
            logger.error(f"Failed to load accounts: {exc}")
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Error loading accounts: {exc}"),
                bgcolor=ft.Colors.RED_400,
            )
            page.snack_bar.open = True
            page.update()

    def _new_account(_):
        """Show dialog to create new account."""
        show_account_dialog(ctx, page, on_save_callback=_refresh_list)

    def _edit_account(account: Account):
        """Show dialog to edit account."""
        show_account_dialog(ctx, page, account=account, on_save_callback=_refresh_list)

    def _delete_account(account: Account):
        """Delete account with confirmation."""
        def _confirm_delete(_):
            try:
                ctx.account_repo.delete(account.id)
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Account '{account.name}' deleted"),
                    bgcolor=ft.Colors.GREEN_400,
                )
                page.snack_bar.open = True
                confirm_dialog.open = False
                page.update()
                _refresh_list()
            except Exception as exc:
                logger.error(f"Failed to delete account: {exc}")
                page.snack_bar = ft.SnackBar(
                    content=ft.Text(f"Error deleting account: {exc}"),
                    bgcolor=ft.Colors.RED_400,
                )
                page.snack_bar.open = True
                confirm_dialog.open = False
                page.update()

        def _cancel_delete(_):
            confirm_dialog.open = False
            page.update()

        confirm_dialog = ft.AlertDialog(
            title=ft.Text("Confirm Delete"),
            content=ft.Text(f"Delete account '{account.name}'? This cannot be undone."),
            actions=[
                ft.TextButton("Cancel", on_click=_cancel_delete),
                ft.ElevatedButton(
                    "Delete",
                    bgcolor=ft.Colors.RED_400,
                    color=ft.Colors.WHITE,
                    on_click=_confirm_delete,
                ),
            ],
        )
        safe_open_dialog(page, confirm_dialog)

    def _close_dialog(_):
        """Close the list dialog."""
        dialog.open = False
        page.update()

    # Account list
    account_list = ft.Column(scroll=ft.ScrollMode.AUTO, spacing=0, height=400)

    # Build dialog
    dialog = ft.AlertDialog(
        title=ft.Row(
            controls=[
                ft.Text("Manage Accounts"),
                ft.Container(expand=True),
                ft.ElevatedButton(
                    "New Account",
                    icon=ft.Icons.ADD,
                    on_click=_new_account,
                ),
            ],
        ),
        content=ft.Container(
            content=account_list,
            width=600,
        ),
        actions=[
            ft.TextButton("Close", on_click=_close_dialog),
        ],
    )

    page.dialog = dialog
    dialog.open = True

    # Load accounts
    _refresh_list()

"""Add Data view - unified interface for creating new entries across all categories."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import flet as ft

from ..components import build_main_layout
from ..components.dialogs import show_budget_dialog, show_category_dialog, show_habit_dialog

if TYPE_CHECKING:
    from ..context import AppContext


def build_add_data_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the add data view with quick access to all creation forms."""

    uid = ctx.require_user_id()

    def notify(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def go_back():
        page.go("/dashboard")

    # Transaction form
    def show_transaction_form():
        """Show inline transaction creation form."""
        accounts = ctx.account_repo.list_all(user_id=uid)
        categories = ctx.category_repo.list_all(user_id=uid)
        if not accounts:
            from ...models.account import Account
            default_acct = ctx.account_repo.create(
                Account(name="Cash", account_type="cash", balance=0.0, user_id=uid),
                user_id=uid,
            )
            accounts = [default_acct]
        if not categories:
            from ...models.category import Category
            default_cat = ctx.category_repo.create(
                Category(name="General", slug="general", category_type="expense", user_id=uid),
                user_id=uid,
            )
            categories = [default_cat]

        account_dd = ft.Dropdown(
            label="Account *",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in accounts if a.id],
            width=300,
        )
        category_dd = ft.Dropdown(
            label="Category *",
            options=[ft.dropdown.Option(str(c.id), c.name) for c in categories if c.id],
            width=300,
        )
        amount_field = ft.TextField(
            label="Amount *",
            hint_text="0.00",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        description_field = ft.TextField(
            label="Description",
            hint_text="What was this for?",
            width=400,
        )
        date_picker = ft.DatePicker(
            on_change=lambda e: date_field.update(),
        )
        page.overlay.append(date_picker)
        date_field = ft.TextField(
            label="Date *",
            value=str(date.today()),
            width=200,
            read_only=True,
            on_click=lambda _: date_picker.pick_date(),
        )

        def save_transaction(_):
            if not account_dd.value:
                notify("Please select an account")
                return
            if not category_dd.value:
                notify("Please select a category")
                return
            if not amount_field.value:
                notify("Please enter an amount")
                return

            try:
                from ...models.transaction import Transaction

                txn = Transaction(
                    account_id=int(account_dd.value),
                    category_id=int(category_dd.value),
                    amount=float(amount_field.value),
                    memo=description_field.value or "",
                    occurred_at=date.fromisoformat(date_field.value),
                    user_id=uid,
                )
                ctx.transaction_repo.create(txn, user_id=uid)
                notify("Transaction created successfully!")
                # Clear form
                amount_field.value = ""
                description_field.value = ""
                amount_field.update()
                description_field.update()
            except Exception as exc:
                notify(f"Failed to create transaction: {exc}")

        def _clear_transaction_form():
            """Clear transaction form fields."""
            amount_field.value = ""
            description_field.value = ""
            amount_field.update()
            description_field.update()

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("New Transaction", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([account_dd, category_dd]),
                    ft.Row([amount_field, date_field]),
                    description_field,
                    ft.Row(
                        [
                            ft.FilledButton("Save Transaction", on_click=save_transaction),
                            ft.TextButton("Clear", on_click=lambda _: _clear_transaction_form()),
                        ]
                    ),
                ],
                spacing=16,
            ),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
        )

    # Habit quick link
    def open_habit_dialog(_):
        show_habit_dialog(ctx, page, habit=None, on_save_callback=lambda: notify("Habit created!"))

    # Budget quick link
    def open_budget_dialog(_):
        show_budget_dialog(
            ctx,
            page,
            target_month=ctx.current_month,
            on_save_callback=lambda: notify("Budget created!"),
        )

    # Category quick link
    def open_category_dialog(_):
        show_category_dialog(ctx, page, category=None, on_save_callback=lambda: notify("Category created!"))

    # Debt/Liability form
    def show_debt_form():
        """Show inline debt creation form."""
        name_field = ft.TextField(label="Debt Name *", width=300)
        balance_field = ft.TextField(label="Current Balance *", width=200, keyboard_type=ft.KeyboardType.NUMBER)
        apr_field = ft.TextField(label="APR (%) *", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        min_payment_field = ft.TextField(label="Minimum Payment *", width=200, keyboard_type=ft.KeyboardType.NUMBER)

        def save_debt(_):
            if not all([name_field.value, balance_field.value, apr_field.value, min_payment_field.value]):
                notify("Please fill in all required fields")
                return

            try:
                from ...models.liability import Liability

                debt = Liability(
                    name=name_field.value,
                    balance=float(balance_field.value),
                    apr=float(apr_field.value),
                    minimum_payment=float(min_payment_field.value),
                    user_id=uid,
                )
                ctx.liability_repo.create(debt, user_id=uid)
                notify("Debt created successfully!")
                # Clear form
                name_field.value = ""
                balance_field.value = ""
                apr_field.value = ""
                min_payment_field.value = ""
                name_field.update()
                balance_field.update()
                apr_field.update()
                min_payment_field.update()
            except Exception as exc:
                notify(f"Failed to create debt: {exc}")

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("New Debt/Liability", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    name_field,
                    ft.Row([balance_field, apr_field, min_payment_field]),
                    ft.FilledButton("Save Debt", on_click=save_debt),
                ],
                spacing=16,
            ),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
        )

    # Portfolio/Holding form
    def show_holding_form():
        """Show inline holding creation form."""
        accounts = ctx.account_repo.list_all(user_id=uid)
        if not accounts:
            from ...models.account import Account
            default_acct = ctx.account_repo.create(
                Account(name="Brokerage", account_type="investment", balance=0.0, user_id=uid),
                user_id=uid,
            )
            accounts = [default_acct]

        account_dd = ft.Dropdown(
            label="Account *",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in accounts if a.id],
            width=300,
        )
        ticker_field = ft.TextField(label="Ticker Symbol *", width=150)
        shares_field = ft.TextField(label="Shares *", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        cost_basis_field = ft.TextField(label="Average Price *", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        market_price_field = ft.TextField(label="Market Price (optional)", width=170, keyboard_type=ft.KeyboardType.NUMBER)

        def save_holding(_):
            if not all([account_dd.value, ticker_field.value, shares_field.value, cost_basis_field.value]):
                notify("Please fill in all required fields")
                return

            try:
                from ...models.holding import Holding

                holding = Holding(
                    account_id=int(account_dd.value),
                    symbol=ticker_field.value.upper(),
                    quantity=float(shares_field.value),
                    avg_price=float(cost_basis_field.value),
                    market_price=float(market_price_field.value or 0.0),
                    user_id=uid,
                )
                ctx.holding_repo.create(holding, user_id=uid)
                notify("Holding created successfully!")
                # Clear form
                ticker_field.value = ""
                shares_field.value = ""
                cost_basis_field.value = ""
                market_price_field.value = ""
                ticker_field.update()
                shares_field.update()
                cost_basis_field.update()
                market_price_field.update()
            except Exception as exc:
                notify(f"Failed to create holding: {exc}")

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("New Portfolio Holding", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    account_dd,
                    ft.Row([ticker_field, shares_field, cost_basis_field, market_price_field]),
                    ft.FilledButton("Save Holding", on_click=save_holding),
                ],
                spacing=16,
            ),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
        )

    # Account form
    def show_account_form():
        """Show inline account creation form."""
        name_field = ft.TextField(label="Account Name *", width=300)
        type_dd = ft.Dropdown(
            label="Account Type *",
            options=[
                ft.dropdown.Option("checking", "Checking"),
                ft.dropdown.Option("savings", "Savings"),
                ft.dropdown.Option("credit", "Credit Card"),
                ft.dropdown.Option("investment", "Investment"),
                ft.dropdown.Option("cash", "Cash"),
            ],
            width=200,
        )
        balance_field = ft.TextField(
            label="Initial Balance",
            value="0.00",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def save_account(_):
            if not name_field.value or not type_dd.value:
                notify("Please fill in all required fields")
                return

            try:
                from ...models.account import Account

                account = Account(
                    name=name_field.value,
                    account_type=type_dd.value,
                    balance=float(balance_field.value or 0),
                    user_id=uid,
                )
                ctx.account_repo.create(account, user_id=uid)
                notify("Account created successfully!")
                # Clear form
                name_field.value = ""
                balance_field.value = "0.00"
                name_field.update()
                balance_field.update()
            except Exception as exc:
                notify(f"Failed to create account: {exc}")

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("New Account", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    name_field,
                    ft.Row([type_dd, balance_field]),
                    ft.FilledButton("Save Account", on_click=save_account),
                ],
                spacing=16,
            ),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
        )

    # Main content layout
    content = ft.Column(
        controls=[
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.IconButton(
                            icon=ft.Icons.ARROW_BACK,
                            on_click=lambda _: go_back(),
                            tooltip="Back to Dashboard",
                        ),
                        ft.Text("Add New Data", size=28, weight=ft.FontWeight.BOLD),
                    ],
                ),
                padding=ft.padding.only(bottom=20),
            ),
            ft.Text(
                "Create new entries for your financial data. Fill out the forms below or use quick action buttons.",
                size=14,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Divider(),
            # Quick action buttons row
            ft.Container(
                content=ft.Row(
                    controls=[
                        ft.ElevatedButton(
                            "New Habit",
                            icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                            on_click=open_habit_dialog,
                        ),
                        ft.ElevatedButton(
                            "New Budget",
                            icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                            on_click=open_budget_dialog,
                        ),
                        ft.ElevatedButton(
                            "New Category",
                            icon=ft.Icons.CATEGORY,
                            on_click=open_category_dialog,
                        ),
                    ],
                    spacing=12,
                    wrap=True,
                ),
                padding=ft.padding.only(bottom=20),
            ),
            # Forms in expandable sections
            ft.Column(
                controls=[
                    show_transaction_form(),
                    show_account_form(),
                    show_debt_form(),
                    show_holding_form(),
                ],
                spacing=20,
                scroll=ft.ScrollMode.AUTO,
                expand=True,
            ),
        ],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.View(
        route="/add-data",
        controls=build_main_layout(ctx, page, "/add-data", content, use_menu_bar=True),
        padding=0,
        scroll=ft.ScrollMode.HIDDEN,
    )

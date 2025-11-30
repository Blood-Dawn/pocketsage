"""Add Data view - unified interface for creating new entries across all categories."""


from __future__ import annotations

import traceback
from calendar import monthrange
from datetime import date, datetime
from typing import TYPE_CHECKING

import flet as ft

from ...devtools import dev_log
from ..components import build_main_layout
from ..constants import (
    ACCOUNT_TYPE_OPTIONS,
    DEFAULT_INCOME_CATEGORY_NAMES,
    HABIT_CADENCE_OPTIONS,
    TRANSACTION_TYPE_OPTIONS,
)

if TYPE_CHECKING:
    from ..context import AppContext


def safe_update_fields(*controls):
    """Safely call `update()` on Flet controls that may not be attached to a page.

    - Skips controls that do not have a `page` attribute set.
    - Suppresses `AssertionError` raised by `update()` when a control
      is not attached to a page (common in tests).
    """
    for control in controls:
        if getattr(control, "page", None):
            try:
                control.update()
            except AssertionError as exc:
                # Best-effort suppression; control may not be attached in tests
                dev_log(None, "Suppressed AssertionError during control.update()", exc=exc)


    # Removed duplicate function definition
def build_add_data_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the add data view with quick access to all creation forms."""

    uid = ctx.require_user_id()
    DEFAULT_CATEGORY_NAMES = [
        "Bonus",
        "Clothing",
        "Coffee",
        "Dining Out",
        "Dividends",
        "Education",
        "Entertainment",
        "Gaming",
        "Gas",
        "Gifts",
        "Groceries",
        "Household",
        "Interest",
        "Internet",
        "Medical",
        "Payment",
        "Pets",
        "Phone",
        "Rebalance",
        "Refund",
        "Rent",
        "Salary",
        "Subscriptions",
        "Transfer In",
        "Transfer Out",
        "Transit",
        "Travel",
        "Utilities",
        "Wellness",
    ]

    ACCOUNT_TEMPLATE_PREFIX = "account-type:"
    PORTFOLIO_ACCOUNT_TYPE_EXTRAS = [
        ("brokerage", "Brokerage"),
        ("retirement", "Retirement"),
        ("401k", "401(k)"),
        ("403b", "403(b)"),
        ("ira", "Traditional IRA"),
        ("roth-ira", "Roth IRA"),
        ("hsa", "HSA"),
        ("529", "529"),
    ]
    INVESTMENT_ACCOUNT_TYPES = {
        "investment",
        "brokerage",
        "retirement",
        "401k",
        "403b",
        "ira",
        "roth-ira",
        "hsa",
        "529",
        "crypto",
    }

    def build_account_options(accounts, option_pairs):
        """Combine existing accounts with quick-add account type templates."""
        normalized_pairs = []
        seen_keys = set()
        for key, label in option_pairs:
            if key in seen_keys:
                continue
            normalized_pairs.append((key, label))
            seen_keys.add(key)

        existing_types = {
            getattr(a, "account_type", None) for a in accounts if getattr(a, "account_type", None)
        }
        options = [ft.dropdown.Option(str(a.id), a.name) for a in accounts if a.id]
        for key, label in normalized_pairs:
            if key not in existing_types:
                options.append(ft.dropdown.Option(f"{ACCOUNT_TEMPLATE_PREFIX}{key}", f"{label} (new account)"))
        if not options:
            options.append(ft.dropdown.Option("0", "Default"))
        return options, {key: label for key, label in normalized_pairs}

    def notify(message: str):
        snack = ft.SnackBar(content=ft.Text(message), open=True)
        page.overlay.append(snack)
        page.update()

    def notify_error(context: str, exc: Exception):
        trace = traceback.format_exc()
        dev_log(ctx.config, f"{context} failed", exc=exc, context={"trace": trace})
        snack = ft.SnackBar(
            content=ft.Text(f"Error: {context}: {exc}"),
            open=True,
        )
        page.overlay.append(snack)
        page.update()

    def go_back():
        page.go("/dashboard")

    # Transaction form
    def show_transaction_form():
        """Show inline transaction creation form."""
        accounts = ctx.account_repo.list_all(user_id=uid)
        categories = ctx.category_repo.list_all(user_id=uid)
        # Ensure default categories are present and ordered
        existing_by_name = {c.name: c for c in categories}
        for name in DEFAULT_CATEGORY_NAMES:
            if name not in existing_by_name:
                from ...models.category import Category

                cat = ctx.category_repo.create(
                    Category(
                        name=name,
                        slug=name.lower().replace(" ", "-"),
                        category_type=(
                            "income"
                            if name in ("Bonus", "Dividends", "Interest", "Salary")
                            else "expense"
                        ),
                        user_id=uid,
                    ),
                    user_id=uid,
                )
                existing_by_name[name] = cat
        categories = [
            existing_by_name[name]
            for name in DEFAULT_CATEGORY_NAMES
            if name in existing_by_name
        ]
        if not accounts:
            from ...models.account import Account
            default_acct = ctx.account_repo.create(
                Account(name="Cash", account_type="cash", balance=0.0, user_id=uid),
                user_id=uid,
            )
            accounts = [default_acct]

        account_options, account_type_lookup = build_account_options(accounts, ACCOUNT_TYPE_OPTIONS)
        account_dd = ft.Dropdown(
            label="Account *",
            options=account_options,
            width=300,
        )
        if account_dd.options:
            account_dd.value = account_dd.options[0].key
        if not account_dd.options:
            account_dd.options = [ft.dropdown.Option("0", "Default")]

        # Transaction type dropdown
        transaction_type_dd = ft.Dropdown(
            label="Type *",
            options=[ft.dropdown.Option(key, label) for key, label in TRANSACTION_TYPE_OPTIONS],
            value="expense",
            width=150,
        )

        # Category dropdown (will be filtered based on transaction type)
        def get_filtered_categories(txn_type: str):
            """Filter categories based on transaction type."""
            if txn_type == "income":
                return [c for c in categories if c.name in DEFAULT_INCOME_CATEGORY_NAMES]
            elif txn_type == "expense":
                return [c for c in categories if c.name not in DEFAULT_INCOME_CATEGORY_NAMES]
            else:  # transfer
                return [c for c in categories if "Transfer" in c.name]

        category_dd = ft.Dropdown(
            label="Category *",
            options=[ft.dropdown.Option(str(c.id), c.name) for c in get_filtered_categories("expense") if c.id],
            width=300,
        )
        if not category_dd.options:
            category_dd.options = [ft.dropdown.Option("0", "General")]

        def on_type_change(e):
            """Update category options when transaction type changes."""
            txn_type = transaction_type_dd.value or "expense"
            filtered = get_filtered_categories(txn_type)
            category_dd.options = [ft.dropdown.Option(str(c.id), c.name) for c in filtered if c.id]
            if not category_dd.options:
                if txn_type == "transfer":
                    category_dd.options = [ft.dropdown.Option("0", "Transfer")]
                else:
                    category_dd.options = [ft.dropdown.Option("0", "General")]
            category_dd.value = None  # Clear selection
            safe_update_fields(category_dd)

        transaction_type_dd.on_change = on_type_change
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
        def on_date_selected(e):
            """Update the date field when a date is picked."""
            if e.control.value:
                # Extract date from datetime object
                selected_date = e.control.value.date() if hasattr(e.control.value, 'date') else e.control.value
                date_field.value = str(selected_date)
                date_field.update()

        date_picker = ft.DatePicker(
            on_change=on_date_selected,
        )
        page.overlay.append(date_picker)
        date_field = ft.TextField(
            label="Date *",
            value=str(date.today()),
            width=200,
            read_only=True,
            on_click=lambda _: (
                setattr(date_picker, "open", True),
                page.update(),
            ),
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

                selected_key = str(account_dd.value or "")
                new_account = None
                if selected_key.startswith(ACCOUNT_TEMPLATE_PREFIX):
                    from ...models.account import Account

                    selected_type = selected_key.replace(ACCOUNT_TEMPLATE_PREFIX, "", 1)
                    account_name = account_type_lookup.get(selected_type, selected_type.title())
                    new_account = ctx.account_repo.create(
                        Account(
                            name=account_name,
                            account_type=selected_type,
                            balance=0.0,
                            user_id=uid,
                        ),
                        user_id=uid,
                    )
                    accounts.append(new_account)
                    account_dd.options, _ = build_account_options(accounts, ACCOUNT_TYPE_OPTIONS)
                    account_dd.value = str(new_account.id or 0)
                    safe_update_fields(account_dd)

                # Parse date and convert to datetime
                date_str = date_field.value or str(date.today())
                parsed_date = date.fromisoformat(date_str)
                occurred_datetime = datetime.combine(parsed_date, datetime.min.time())

                account_id = (
                    int(account_dd.value or 0)
                    if not new_account
                    else int(new_account.id or 0)
                )
                # Get the selected account to check if it's an investment account
                selected_account = new_account or next((a for a in accounts if a.id == account_id), None)

                # Get transaction type and set amount sign accordingly
                # Transaction model uses: positive for income, negative for expense
                txn_type = transaction_type_dd.value or "expense"
                raw_amount = float(amount_field.value)
                signed_amount = raw_amount if txn_type == "income" else -abs(raw_amount)

                txn = Transaction(
                    account_id=account_id,
                    category_id=int(category_dd.value or 0),
                    amount=signed_amount,
                    memo=description_field.value or "",
                    occurred_at=occurred_datetime,
                    user_id=uid,
                )
                created_txn = ctx.transaction_repo.create(txn, user_id=uid)
                dev_log(
                    ctx.config,
                    "Transaction saved",
                    context={"amount": txn.amount, "memo": txn.memo},
                )

                # Check if this is an investment account - if so, prompt for holding details
                if selected_account and selected_account.account_type in INVESTMENT_ACCOUNT_TYPES:
                    show_investment_details_dialog(created_txn, selected_account)
                else:
                    notify("Transaction created successfully!")
                    # Clear form
                    amount_field.value = ""
                    description_field.value = ""
                    safe_update_fields(amount_field, description_field)
            except Exception as exc:
                notify_error("Create transaction", exc)

        def show_investment_details_dialog(transaction, account):
            """Show dialog to capture investment-specific details for portfolio sync."""
            symbol_field = ft.TextField(
                label="Stock Symbol *",
                hint_text="e.g., AAPL, TSLA, SPY",
                width=150,
                autofocus=True,
            )
            shares_field = ft.TextField(
                label="Number of Shares *",
                hint_text="e.g., 10",
                width=150,
                keyboard_type=ft.KeyboardType.NUMBER,
            )
            skip_holding = ft.Checkbox(
                label="Skip portfolio sync (transfer/dividend/etc.)",
                value=False,
            )

            def save_holding(_):
                # Allow skipping if it's not a buy/sell transaction
                if skip_holding.value:
                    dialog.open = False
                    page.update()
                    notify("Transaction saved (portfolio not updated)")
                    # Clear form
                    amount_field.value = ""
                    description_field.value = ""
                    safe_update_fields(amount_field, description_field)
                    return

                if not symbol_field.value or not shares_field.value:
                    notify("Please enter stock symbol and number of shares")
                    return

                try:
                    from ...models.portfolio import Holding

                    symbol = symbol_field.value.strip().upper()
                    shares = float(shares_field.value)
                    transaction_amount = abs(float(transaction.amount))

                    # Check if holding exists for this symbol
                    existing_holdings = ctx.holding_repo.list_all(user_id=uid)
                    existing = next(
                        (h for h in existing_holdings if h.symbol == symbol and h.account_id == account.id),
                        None
                    )

                    # Determine if this is a buy (expense) or sell (income)
                    txn_type = transaction_type_dd.value or "expense"
                    is_buy = txn_type == "expense" or transaction.amount < 0

                    if existing:
                        # Update existing holding
                        if is_buy:
                            # Buy: increase shares and update avg price
                            old_total_cost = existing.quantity * existing.avg_price
                            new_total_cost = old_total_cost + transaction_amount
                            new_quantity = existing.quantity + shares
                            existing.quantity = new_quantity
                            existing.avg_price = new_total_cost / new_quantity if new_quantity > 0 else 0
                        else:
                            # Sell: decrease shares
                            new_quantity = existing.quantity - shares
                            if new_quantity > 0:
                                existing.quantity = new_quantity
                            else:
                                # Sold all shares, delete holding
                                ctx.holding_repo.delete(existing.id, user_id=uid)
                                dialog.open = False
                                page.update()
                                notify("Transaction and portfolio updated (holding removed)")
                                amount_field.value = ""
                                description_field.value = ""
                                safe_update_fields(amount_field, description_field)
                                return

                        ctx.holding_repo.update(existing, user_id=uid)
                    else:
                        # Create new holding (only for buys)
                        if is_buy:
                            price_per_share = transaction_amount / shares if shares > 0 else 0
                            holding = Holding(
                                user_id=uid,
                                symbol=symbol,
                                quantity=shares,
                                avg_price=price_per_share,
                                market_price=price_per_share,
                                account_id=account.id,
                                acquired_at=transaction.occurred_at,
                            )
                            ctx.holding_repo.create(holding, user_id=uid)
                        else:
                            notify("Warning: Cannot sell shares you don't own. Transaction saved but portfolio not updated.")

                    dialog.open = False
                    page.update()
                    notify("Transaction and portfolio updated successfully!")
                    # Clear form
                    amount_field.value = ""
                    description_field.value = ""
                    safe_update_fields(amount_field, description_field)
                except Exception as exc:
                    notify_error("Update portfolio", exc)

            def close_dialog(_):
                dialog.open = False
                page.update()
                # Still clear the form even if they cancel
                amount_field.value = ""
                description_field.value = ""
                safe_update_fields(amount_field, description_field)

            dialog = ft.AlertDialog(
                modal=True,
                title=ft.Text("Investment Details"),
                content=ft.Column(
                    controls=[
                        ft.Text(
                            f"Transaction: ${abs(transaction.amount):.2f} in {account.name}",
                            size=14,
                            weight=ft.FontWeight.W_500,
                        ),
                        ft.Text(
                            "Add stock details to sync with portfolio:",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.Container(height=8),
                        symbol_field,
                        shares_field,
                        ft.Container(height=8),
                        skip_holding,
                    ],
                    tight=True,
                    spacing=8,
                    width=350,
                ),
                actions=[
                    ft.TextButton("Skip", on_click=close_dialog),
                    ft.FilledButton("Save to Portfolio", on_click=save_holding),
                ],
            )
            page.dialog = dialog
            dialog.open = True
            page.update()
        def _clear_transaction_form():
            """Clear transaction form fields."""
            amount_field.value = ""
            description_field.value = ""
            safe_update_fields(amount_field, description_field)

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("New Transaction", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([account_dd, transaction_type_dd, category_dd], spacing=10),
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

    def show_budget_form():
        """Inline budget creation with a single planned line."""
        label_field = ft.TextField(
            label="Budget Name",
            value=f"Budget {ctx.current_month:%B %Y}",
            width=260,
        )
        category_dd = ft.Dropdown(
            label="Category",
            options=[
                ft.dropdown.Option(str(c.id), c.name)
                for c in ctx.category_repo.list_all(user_id=uid)
                if c.id
            ],
            width=240,
        )
        amount_field = ft.TextField(
            label="Planned amount",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def save_budget(_):
            if not amount_field.value:
                notify("Planned amount required")
                return
            from ...models.budget import Budget, BudgetLine

            budget = ctx.budget_repo.get_for_month(
                ctx.current_month.year,
                ctx.current_month.month,
                user_id=uid,
            )
            if not budget:
                start = ctx.current_month.replace(day=1)
                end = ctx.current_month.replace(
                    day=monthrange(
                        ctx.current_month.year,
                        ctx.current_month.month
                    )[1]
                )
                budget = ctx.budget_repo.create(
                    Budget(
                        period_start=start,
                        period_end=end,
                        label=label_field.value or "",
                        user_id=uid,
                    ),
                    user_id=uid,
                )
            line_cat = int(category_dd.value) if category_dd.value else None
            if line_cat is not None and budget is not None and budget.id is not None:
                ctx.budget_repo.create_line(
                    BudgetLine(
                        budget_id=int(budget.id),
                        category_id=int(line_cat),
                        planned_amount=float(amount_field.value or 0),
                        rollover_enabled=False,
                        user_id=uid,
                    ),
                    user_id=uid,
                )
            notify("Budget saved")

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("New Budget", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row(
                        [label_field, category_dd, amount_field],
                        spacing=10,
                        wrap=True,
                        run_spacing=8,
                    ),
                    ft.FilledButton("Save Budget", on_click=save_budget),
                ],
                spacing=12,
            ),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
        )

    # Habit inline form
    def show_habit_form():
        name_field = ft.TextField(label="Habit Name *", width=260)
        desc_field = ft.TextField(label="Description", width=320)
        cadence_dd = ft.Dropdown(
            label="Cadence",
            options=[ft.dropdown.Option(key, label) for key, label in HABIT_CADENCE_OPTIONS],
            value="daily",
            width=200,
        )

        def save_habit(_):
            if not (name_field.value or "").strip():
                notify("Habit name required")
                return
            from ...models.habit import Habit

            habit = Habit(
                name=(name_field.value or "").strip(),
                description=desc_field.value or "",
                cadence=cadence_dd.value or "daily",
                user_id=uid,
            )
            ctx.habit_repo.create(habit, user_id=uid)
            notify("Habit created")
            name_field.value = ""
            desc_field.value = ""
            safe_update_fields(name_field, desc_field)

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("New Habit", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([name_field, cadence_dd], spacing=10, wrap=True, run_spacing=8),
                    desc_field,
                    ft.FilledButton("Save Habit", on_click=save_habit),
                ],
                spacing=12,
            ),
            padding=20,
            border=ft.border.all(1, ft.Colors.OUTLINE),
            border_radius=8,
        )

    # Debt/Liability form
    def show_debt_form():
        """Show inline debt creation form."""
        name_field = ft.TextField(label="Debt Name *", width=300)
        balance_field = ft.TextField(
            label="Current Balance *",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        apr_field = ft.TextField(label="APR (%) *", width=150, keyboard_type=ft.KeyboardType.NUMBER)
        min_payment_field = ft.TextField(
            label="Minimum Payment *",
            width=200,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def save_debt(_):
            if not all([
                name_field.value,
                balance_field.value,
                apr_field.value,
                min_payment_field.value,
            ]):
                notify("Please fill in all required fields")
                return

            try:
                from ...models.liability import Liability

                debt = Liability(
                    name=name_field.value or "",
                    balance=float(balance_field.value or "0.0"),
                    apr=float(apr_field.value or "0.0"),
                    minimum_payment=float(min_payment_field.value or "0.0"),
                    user_id=uid,
                )
                ctx.liability_repo.create(debt, user_id=uid)
                dev_log(
                    ctx.config,
                    "Liability created",
                    context={
                        "name": debt.name,
                        "balance": debt.balance,
                    },
                )
                notify("Debt created successfully!")
                # Clear form
                name_field.value = ""
                balance_field.value = ""
                apr_field.value = ""
                min_payment_field.value = ""
                safe_update_fields(name_field, balance_field, apr_field, min_payment_field)
            except Exception as exc:
                notify_error("Create debt", exc)

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

        holding_option_pairs = ACCOUNT_TYPE_OPTIONS + PORTFOLIO_ACCOUNT_TYPE_EXTRAS
        account_options, holding_account_type_lookup = build_account_options(accounts, holding_option_pairs)
        account_dd = ft.Dropdown(
            label="Account *",
            options=account_options,
            width=300,
        )
        if account_dd.options:
            account_dd.value = account_dd.options[0].key
        if not account_dd.options:
            account_dd.options = [ft.dropdown.Option("0", "Default")]
        ticker_field = ft.TextField(label="Ticker Symbol *", width=150)
        shares_field = ft.TextField(
            label="Shares *",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        cost_basis_field = ft.TextField(
            label="Average Price *",
            width=150,
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        market_price_field = ft.TextField(
            label="Market Price (optional)",
            width=170,
            keyboard_type=ft.KeyboardType.NUMBER,
        )

        def save_holding(_):
            # Ensure holding_account_type_lookup is accessible via closure
            nonlocal holding_account_type_lookup

            if not all([
                account_dd.value,
                ticker_field.value,
                shares_field.value,
                cost_basis_field.value,
            ]):
                notify("Please fill in all required fields")
                return

            try:
                from ...models.portfolio import Holding

                selected_key = str(account_dd.value or "")
                if selected_key.startswith(ACCOUNT_TEMPLATE_PREFIX):
                    from ...models.account import Account

                    selected_type = selected_key.replace(ACCOUNT_TEMPLATE_PREFIX, "", 1)
                    account_name = holding_account_type_lookup.get(selected_type, selected_type.title())
                    new_account = ctx.account_repo.create(
                        Account(
                            name=account_name,
                            account_type=selected_type,
                            balance=0.0,
                            user_id=uid,
                        ),
                        user_id=uid,
                    )
                    accounts.append(new_account)
                    account_dd.options, _ = build_account_options(accounts, holding_option_pairs)
                    account_dd.value = str(new_account.id or 0)
                    safe_update_fields(account_dd)
                    account_id = int(new_account.id or 0)
                else:
                    account_id = int(account_dd.value or 0)

                holding = Holding(
                    account_id=account_id,
                    symbol=(ticker_field.value or "").upper(),
                    quantity=float(shares_field.value or "0.0"),
                    avg_price=float(cost_basis_field.value or "0.0"),
                    market_price=float(market_price_field.value or 0.0),
                    user_id=uid,
                )
                ctx.holding_repo.create(holding, user_id=uid)
                dev_log(
                    ctx.config,
                    "Holding created",
                    context={
                        "symbol": holding.symbol,
                        "qty": holding.quantity,
                    },
                )
                notify("Holding created successfully!")
                # Clear form
                ticker_field.value = ""
                shares_field.value = ""
                cost_basis_field.value = ""
                market_price_field.value = ""
                safe_update_fields(ticker_field, shares_field, cost_basis_field, market_price_field)
            except Exception as exc:
                notify_error("Create holding", exc)

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
            value=ACCOUNT_TYPE_OPTIONS[0][0],
            options=[ft.dropdown.Option(key, label) for key, label in ACCOUNT_TYPE_OPTIONS],
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
                dev_log(
                    ctx.config,
                    "Account created",
                    context={
                        "name": account.name,
                        "type": account.account_type,
                    },
                )
                notify("Account created successfully!")
                # Clear form
                name_field.value = ""
                balance_field.value = "0.00"
                safe_update_fields(name_field, balance_field)
            except Exception as exc:
                notify_error("Create account", exc)

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
                (
                    "Create new entries for your financial data. "
                    "Fill out the forms below or use quick action buttons."
                ),
                size=14,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Divider(),
            # Quick action buttons row
            # Quick action buttons removed; rely on inline forms below.
            # Forms in expandable sections
            ft.Column(
                controls=[
                    show_transaction_form(),
                    show_account_form(),
                    show_habit_form(),
                    show_debt_form(),
                    show_budget_form(),
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

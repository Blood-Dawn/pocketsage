"""Add Data view - unified interface for creating new entries across all categories."""

from __future__ import annotations

import traceback
from calendar import monthrange
from contextlib import suppress
from datetime import date, datetime
from typing import TYPE_CHECKING

import flet as ft

from ...devtools import dev_log
from ..constants import (
    ACCOUNT_TYPE_OPTIONS,
    DEFAULT_CATEGORY_SEED,
)
from ..components import build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_add_data_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the add data view with quick access to all creation forms."""

    uid = ctx.require_user_id()

    def notify(message: str) -> None:
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    def notify_error(context: str, exc: Exception) -> None:
        trace = traceback.format_exc()
        dev_log(ctx.config, "Add data action failed", exc=exc, context={"action": context})
        print(f"{context} failed: {exc}\n{trace}")
        notify(f"Error: {context}")

    def go_back() -> None:
        page.go("/dashboard")
        page.update()

    def _ensure_default_categories():
        from ...models.category import Category

        categories = ctx.category_repo.list_all(user_id=uid)
        existing_by_slug = {c.slug: c for c in categories}
        ordered: list[Category] = []

        for seed in DEFAULT_CATEGORY_SEED:
            slug = seed["slug"]
            existing = existing_by_slug.get(slug)
            if existing is None:
                category = Category(
                    name=seed["name"],
                    slug=slug,
                    category_type=seed.get("category_type", "expense"),
                    color=seed.get("color"),
                    user_id=uid,
                )
                existing = ctx.category_repo.upsert_by_slug(category, user_id=uid)
                existing_by_slug[slug] = existing
            else:
                updated = False
                if existing.name != seed["name"]:
                    existing.name = seed["name"]
                    updated = True
                if existing.category_type != seed.get("category_type", existing.category_type):
                    existing.category_type = seed.get("category_type", existing.category_type)
                    updated = True
                if existing.color is None and seed.get("color"):
                    existing.color = seed["color"]
                    updated = True
                if updated:
                    existing = ctx.category_repo.update(existing, user_id=uid)
            ordered.append(existing)

        seed_slugs = {c["slug"] for c in DEFAULT_CATEGORY_SEED}
        extras = [c for c in categories if c.slug not in seed_slugs]
        ordered.extend(sorted(extras, key=lambda c: c.name.lower()))
        return ordered

    # Transaction form
    def show_transaction_form():
        """Show inline transaction creation form."""

        accounts = ctx.account_repo.list_all(user_id=uid)
        if not accounts:
            from ...models.account import Account

            default_acct = ctx.account_repo.create(
                Account(name="Cash", account_type="cash", balance=0.0, user_id=uid),
                user_id=uid,
            )
            accounts = [default_acct]

        categories = _ensure_default_categories()

        account_dd = ft.Dropdown(
            label="Account *",
            options=[
                ft.dropdown.Option(
                    str(a.id),
                    f"{a.name} ({(a.account_type or 'account').title()})",
                )
                for a in accounts
                if a.id
            ],
            width=300,
        )
        if account_dd.options:
            account_dd.value = account_dd.options[0].key
        category_dd = ft.Dropdown(
            label="Category *",
            options=[ft.dropdown.Option(str(c.id), c.name) for c in categories if c.id],
            width=300,
        )
        if category_dd.options:
            category_dd.value = category_dd.options[0].key

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
        date_picker = ft.DatePicker(on_change=lambda e: date_field.update())
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

                parsed_date = date.fromisoformat(date_field.value or str(date.today()))
                occurred_datetime = datetime.combine(parsed_date, datetime.min.time())
                amount = float(amount_field.value)

                txn = Transaction(
                    account_id=int(account_dd.value or 0),
                    category_id=int(category_dd.value or 0),
                    amount=amount,
                    memo=description_field.value or "",
                    occurred_at=occurred_datetime,
                    user_id=uid,
                )
                ctx.transaction_repo.create(txn, user_id=uid)
                notify("Transaction created successfully!")
                amount_field.value = ""
                description_field.value = ""
                with suppress(AssertionError):
                    amount_field.update()
                    description_field.update()
            except Exception as exc:
                notify_error("Create transaction", exc)

        def _clear_transaction_form():
            amount_field.value = ""
            description_field.value = ""
            for fld in (amount_field, description_field):
                if getattr(fld, "page", None):
                    with suppress(AssertionError):
                        fld.update()

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

    def show_budget_form():
        """Inline budget creation with a single planned line."""

        label_field = ft.TextField(
            label="Budget Name",
            value=f"Budget {ctx.current_month:%B %Y}",
            width=260,
        )
        categories = _ensure_default_categories()
        category_dd = ft.Dropdown(
            label="Category",
            options=[ft.dropdown.Option(str(c.id), c.name) for c in categories if c.id],
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
                end = ctx.current_month.replace(day=monthrange(ctx.current_month.year, ctx.current_month.month)[1])
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

    def show_habit_form():
        """Habit inline form."""

        name_field = ft.TextField(label="Habit Name *", width=260)
        desc_field = ft.TextField(label="Description", width=320)
        cadence_dd = ft.Dropdown(
            label="Cadence",
            options=[
                ft.dropdown.Option("daily", "Daily"),
                ft.dropdown.Option("weekly", "Weekly"),
                ft.dropdown.Option("biweekly", "Bi-Weekly"),
                ft.dropdown.Option("monthly", "Monthly"),
                ft.dropdown.Option("yearly", "Yearly"),
            ],
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
            with suppress(AssertionError):
                name_field.update()
                desc_field.update()

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
            if not all(
                [
                    name_field.value,
                    balance_field.value,
                    apr_field.value,
                    min_payment_field.value,
                ]
            ):
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
                dev_log(ctx.config, "Liability created", context={"name": debt.name})
                notify("Debt created successfully!")
                balance_field.value = ""
                apr_field.value = ""
                min_payment_field.value = ""
                with suppress(AssertionError):
                    balance_field.update()
                    apr_field.update()
                    min_payment_field.update()
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

        account_dd = ft.Dropdown(
            label="Account *",
            options=[ft.dropdown.Option(str(a.id), a.name) for a in accounts if a.id],
            width=300,
        )
        if account_dd.options:
            account_dd.value = account_dd.options[0].key

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
            if not all(
                [
                    account_dd.value,
                    ticker_field.value,
                    shares_field.value,
                    cost_basis_field.value,
                ]
            ):
                notify("Please fill in all required fields")
                return

            try:
                from ...models.portfolio import Holding

                holding = Holding(
                    account_id=int(account_dd.value or 0),
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
                ticker_field.value = ""
                shares_field.value = ""
                cost_basis_field.value = ""
                with suppress(AssertionError):
                    ticker_field.update()
                    shares_field.update()
                    cost_basis_field.update()
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
            options=[ft.dropdown.Option(key, text) for key, text in ACCOUNT_TYPE_OPTIONS],
            width=240,
            value="checking",
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
                name_field.value = ""
                balance_field.value = "0.00"
                with suppress(AssertionError):
                    name_field.update()
                    balance_field.update()
            except Exception as exc:
                notify_error("Create account", exc)

        return ft.Container(
            content=ft.Column(
                controls=[
                    ft.Text("New Account", size=20, weight=ft.FontWeight.BOLD),
                    ft.Divider(),
                    ft.Row([name_field, type_dd, balance_field], wrap=True, spacing=10),
                    ft.FilledButton("Save Account", on_click=save_account),
                ],
                spacing=12,
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
                    "Fill out the forms below to quickly capture transactions, accounts, habits, debts, and holdings."
                ),
                size=14,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Divider(),
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

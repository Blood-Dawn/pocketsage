"""Dashboard view implementation."""

from __future__ import annotations

from datetime import datetime, timedelta, date
from typing import TYPE_CHECKING

import flet as ft

from ..charts import cashflow_trend_png, spending_chart_png
from ..components import build_app_bar, build_main_layout, build_stat_card
from ...models.habit import HabitEntry

if TYPE_CHECKING:
    from ..context import AppContext


def build_dashboard_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the dashboard view."""

    # Fetch summary data
    today = datetime.now()

    # Get monthly summary
    monthly_summary = ctx.transaction_repo.get_monthly_summary(today.year, today.month)
    income = monthly_summary.get("income", 0)
    expenses = monthly_summary.get("expenses", 0)
    net = monthly_summary.get("net", 0)

    # Get account balances (net worth)
    accounts = ctx.account_repo.list_all()
    net_worth = sum(ctx.account_repo.get_balance(acc.id) for acc in accounts if acc.id)

    # Get total debt
    total_debt = ctx.liability_repo.get_total_debt()

    # Get active habits
    active_habits = ctx.habit_repo.list_active()
    habit_count = len(active_habits)

    # Build stat cards
    stat_cards = ft.Row(
        [
            ft.Container(
                content=build_stat_card(
                    "Net Worth",
                    f"${net_worth:,.2f}",
                    icon=ft.Icons.ACCOUNT_BALANCE_WALLET,
                    color=ft.Colors.PRIMARY,
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "This Month's Income",
                    f"${income:,.2f}",
                    icon=ft.Icons.TRENDING_UP,
                    color=ft.Colors.GREEN,
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "This Month's Expenses",
                    f"${expenses:,.2f}",
                    icon=ft.Icons.TRENDING_DOWN,
                    color=ft.Colors.ORANGE,
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "Net This Month",
                    f"${net:,.2f}",
                    icon=ft.Icons.MONETIZATION_ON,
                    color=ft.Colors.GREEN if net >= 0 else ft.Colors.RED,
                ),
                expand=True,
            ),
        ],
        spacing=16,
    )

    # Second row of stats
    secondary_stats = ft.Row(
        [
            ft.Container(
                content=build_stat_card(
                    "Total Debt",
                    f"${total_debt:,.2f}",
                    icon=ft.Icons.CREDIT_CARD,
                    color=ft.Colors.RED if total_debt > 0 else ft.Colors.GREEN,
                    subtitle=f"{len(ctx.liability_repo.list_active())} active liabilities",
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "Active Habits",
                    str(habit_count),
                    icon=ft.Icons.CHECK_CIRCLE,
                    color=ft.Colors.BLUE,
                    subtitle="Track your daily progress",
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "Accounts",
                    str(len(accounts)),
                    icon=ft.Icons.ACCOUNT_BALANCE,
                    color=ft.Colors.PURPLE,
                    subtitle="Linked accounts",
                ),
                expand=True,
            ),
        ],
        spacing=16,
    )

    # Recent transactions section
    recent_txns = ctx.transaction_repo.list_all(limit=5)
    txn_rows = []

    for txn in recent_txns:
        amount_color = ft.Colors.GREEN if txn.amount > 0 else ft.Colors.RED
        txn_rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(
                            txn.occurred_at.strftime("%Y-%m-%d"),
                            size=14,
                            width=100,
                        ),
                        ft.Text(
                            txn.memo[:40] if len(txn.memo) > 40 else txn.memo,
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
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                padding=10,
                border=ft.border.only(bottom=ft.border.BorderSide(1, ft.Colors.OUTLINE_VARIANT)),
            )
        )

    if not txn_rows:
        txn_rows.append(
            ft.Container(
                content=ft.Text(
                    "No recent transactions",
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                padding=20,
            )
        )

    recent_txns_card = ft.Card(
        content=ft.Column(
            [
                ft.Container(
                    content=ft.Text(
                        "Recent Transactions",
                        size=18,
                        weight=ft.FontWeight.BOLD,
                    ),
                    padding=16,
                ),
                ft.Divider(height=1),
                ft.Column(txn_rows, spacing=0),
            ],
            spacing=0,
        ),
        elevation=2,
    )

    # Quick actions
    quick_actions = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Quick Actions", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Add Transaction",
                                icon=ft.Icons.ADD,
                                on_click=lambda _: page.go("/ledger"),
                            ),
                            ft.FilledButton(
                                "Track Habit",
                                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                                on_click=lambda _: page.go("/habits"),
                            ),
                            ft.FilledButton(
                                "View Budget",
                                icon=ft.Icons.ACCOUNT_BALANCE,
                                on_click=lambda _: page.go("/budgets"),
                            ),
                        ],
                        spacing=16,
                    ),
                ],
            ),
            padding=16,
        ),
        elevation=2,
    )

    # Charts
    month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    month_txs = ctx.transaction_repo.filter_by_date_range(month_start, next_month)
    spending_png = None
    try:
        spending_png = spending_chart_png(month_txs)
    except Exception:
        spending_png = None

    # Cashflow trend: pull a wider slice
    all_recent = ctx.transaction_repo.list_all(limit=500)
    try:
        cashflow_png = cashflow_trend_png(all_recent, months=6)
    except Exception:
        cashflow_png = None

    charts_row = ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=ft.Column(
                        [
                            ft.Text("Spending by Category (This Month)", weight=ft.FontWeight.BOLD),
                            ft.Image(src=str(spending_png), height=260) if spending_png else ft.Text("Chart unavailable"),
                        ],
                        spacing=8,
                    ),
                    col={"sm": 12, "md": 6},
                ),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Cashflow (Last 6 months)", weight=ft.FontWeight.BOLD),
                            ft.Image(src=str(cashflow_png), height=260) if cashflow_png else ft.Text("Chart unavailable"),
                        ],
                        spacing=8,
                    ),
                col={"sm": 12, "md": 6},
            ),
        ],
        run_spacing=16,
        spacing=16,
    )

    # Upcoming payments (next 30 days)
    upcoming_rows = []
    horizon = date.today() + timedelta(days=30)
    for liability in ctx.liability_repo.list_all():
        due_day = getattr(liability, "due_day", 1) or 1
        next_due = date.today().replace(day=min(due_day, 28))
        if next_due < date.today():
            # shift to next month
            next_month = (next_due.replace(day=1) + timedelta(days=31)).replace(day=due_day)
            next_due = next_month
        if next_due <= horizon:
            upcoming_rows.append(
                ft.ListTile(
                    title=ft.Text(liability.name),
                    subtitle=ft.Text(f"Due {next_due.isoformat()}"),
                    trailing=ft.Text(f"${liability.minimum_payment:,.2f}"),
                    on_click=lambda _, lid=liability.id: page.go("/debts"),
                )
            )
    if not upcoming_rows:
        upcoming_rows.append(ft.Text("No payments due in next 30 days.", color=ft.Colors.ON_SURFACE_VARIANT))

    # Today's habits quick toggle
    today_habit_rows = []
    today_date = date.today()
    for habit in active_habits:
        entry = ctx.habit_repo.get_entry(habit.id, today_date)
        is_done = entry is not None and entry.value > 0

        def toggle(_e, hid=habit.id):
            cur = ctx.habit_repo.get_entry(hid, today_date)
            if cur:
                ctx.habit_repo.delete_entry(hid, today_date)
            else:
                ctx.habit_repo.upsert_entry(HabitEntry(habit_id=hid, occurred_on=today_date, value=1))
            page.snack_bar = ft.SnackBar(content=ft.Text("Habit updated"))
            page.snack_bar.open = True
            page.update()

        today_habit_rows.append(
            ft.ListTile(
                title=ft.Text(habit.name),
                trailing=ft.Switch(value=is_done, on_change=toggle),
                subtitle=ft.Text(f"Current streak: {ctx.habit_repo.get_current_streak(habit.id)}"),
                on_click=lambda _, hid=habit.id: page.go("/habits"),
            )
        )
    if not today_habit_rows:
        today_habit_rows.append(ft.Text("No active habits yet.", color=ft.Colors.ON_SURFACE_VARIANT))

    secondary_stats = ft.ResponsiveRow(
        controls=[
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Upcoming Payments (30 days)", size=16, weight=ft.FontWeight.BOLD),
                        ft.Column(upcoming_rows, spacing=4),
                    ]
                ),
                col={"sm": 12, "md": 6},
            ),
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text("Today's Habits", size=16, weight=ft.FontWeight.BOLD),
                        ft.Column(today_habit_rows, spacing=4),
                    ]
                ),
                col={"sm": 12, "md": 6},
            ),
        ],
        run_spacing=16,
        spacing=16,
    )

    # Build content
    content = ft.Column(
        [
            stat_cards,
            ft.Container(height=16),
            charts_row,
            ft.Container(height=24),
            secondary_stats,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Dashboard", page)
    main_layout = build_main_layout(ctx, page, "/dashboard", content)

    return ft.View(
        route="/dashboard",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

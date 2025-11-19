"""Dashboard view implementation."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING

import flet as ft

from ..components import build_app_bar, build_main_layout, build_stat_card

if TYPE_CHECKING:
    from ..context import AppContext


def build_dashboard_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the dashboard view."""

    # Fetch summary data
    today = datetime.now()
    start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end_of_month = (start_of_month + timedelta(days=32)).replace(day=1) - timedelta(seconds=1)

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
                    icon=ft.icons.ACCOUNT_BALANCE_WALLET,
                    color=ft.colors.PRIMARY,
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "This Month's Income",
                    f"${income:,.2f}",
                    icon=ft.icons.TRENDING_UP,
                    color=ft.colors.GREEN,
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "This Month's Expenses",
                    f"${expenses:,.2f}",
                    icon=ft.icons.TRENDING_DOWN,
                    color=ft.colors.ORANGE,
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "Net This Month",
                    f"${net:,.2f}",
                    icon=ft.icons.MONETIZATION_ON,
                    color=ft.colors.GREEN if net >= 0 else ft.colors.RED,
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
                    icon=ft.icons.CREDIT_CARD,
                    color=ft.colors.RED if total_debt > 0 else ft.colors.GREEN,
                    subtitle=f"{len(ctx.liability_repo.list_active())} active liabilities",
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "Active Habits",
                    str(habit_count),
                    icon=ft.icons.CHECK_CIRCLE,
                    color=ft.colors.BLUE,
                    subtitle="Track your daily progress",
                ),
                expand=True,
            ),
            ft.Container(
                content=build_stat_card(
                    "Accounts",
                    str(len(accounts)),
                    icon=ft.icons.ACCOUNT_BALANCE,
                    color=ft.colors.PURPLE,
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
        amount_color = ft.colors.GREEN if txn.amount > 0 else ft.colors.RED
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
                border=ft.border.only(
                    bottom=ft.border.BorderSide(1, ft.colors.OUTLINE_VARIANT)
                ),
            )
        )

    if not txn_rows:
        txn_rows.append(
            ft.Container(
                content=ft.Text(
                    "No recent transactions",
                    color=ft.colors.ON_SURFACE_VARIANT,
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
                                icon=ft.icons.ADD,
                                on_click=lambda _: page.go("/ledger"),
                            ),
                            ft.FilledButton(
                                "Track Habit",
                                icon=ft.icons.CHECK_CIRCLE_OUTLINE,
                                on_click=lambda _: page.go("/habits"),
                            ),
                            ft.FilledButton(
                                "View Budget",
                                icon=ft.icons.ACCOUNT_BALANCE,
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

    # Build content
    content = ft.Column(
        [
            stat_cards,
            ft.Container(height=16),
            secondary_stats,
            ft.Container(height=24),
            recent_txns_card,
            ft.Container(height=16),
            quick_actions,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Dashboard")
    main_layout = build_main_layout(page, "/dashboard", content)

    return ft.View(
        route="/dashboard",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

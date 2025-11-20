"""Debts view implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ...services.debts import DebtAccount, avalanche_schedule, snowball_schedule
from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_debts_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the debts/liabilities view."""

    uid = ctx.require_user_id()
    # Get all liabilities
    liabilities = ctx.liability_repo.list_all(user_id=uid)

    # Calculate totals
    total_debt = ctx.liability_repo.get_total_debt(user_id=uid)
    weighted_apr = ctx.liability_repo.get_weighted_apr(user_id=uid)
    total_min_payment = sum(liability.minimum_payment for liability in liabilities)

    # Summary cards
    summary = ft.Row(
        [
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Total Debt", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(
                                f"${total_debt:,.2f}",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=ft.Colors.RED,
                            ),
                        ],
                    ),
                    padding=20,
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Weighted APR", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(f"{weighted_apr:.2f}%", size=28, weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    padding=20,
                ),
                expand=True,
            ),
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Min. Payment", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(
                                f"${total_min_payment:,.2f}", size=28, weight=ft.FontWeight.BOLD
                            ),
                        ],
                    ),
                    padding=20,
                ),
                expand=True,
            ),
        ],
        spacing=16,
    )

    def to_accounts() -> list[DebtAccount]:
        return [
            DebtAccount(
                id=lb.id or 0,
                balance=lb.balance,
                apr=lb.apr,
                minimum_payment=lb.minimum_payment,
                statement_due_day=getattr(lb, "due_day", 1) or 1,
            )
            for lb in liabilities
        ]

    strategy_state = {"value": "snowball"}

    def run_projection(strategy: str):
        debts = to_accounts()
        if strategy == "avalanche":
            sched = avalanche_schedule(debts=debts, surplus=0.0)
        else:
            sched = snowball_schedule(debts=debts, surplus=0.0)
        payoff = None
        if sched:
            payoff = sched[-1]["date"]
        return sched, payoff

    schedule_rows, payoff_date = run_projection(strategy_state["value"])
    payoff_text = ft.Text(
        f"Projected payoff: {payoff_date or 'N/A'}", size=14, color=ft.Colors.ON_SURFACE_VARIANT
    )

    # Liability list
    liability_rows = []

    for liability in liabilities:
        monthly_interest = liability.balance * (liability.apr / 100) / 12

        liability_rows.append(
            ft.DataRow(
                cells=[
                    ft.DataCell(ft.Text(liability.name)),
                    ft.DataCell(ft.Text(f"${liability.balance:,.2f}")),
                    ft.DataCell(ft.Text(f"{liability.apr:.2f}%")),
                    ft.DataCell(ft.Text(f"${liability.minimum_payment:,.2f}")),
                    ft.DataCell(ft.Text(f"${monthly_interest:,.2f}")),
                ]
            )
        )

    if not liability_rows:
        liability_rows.append(
            ft.DataRow(cells=[ft.DataCell(ft.Text("No liabilities found")) for _ in range(5)])
        )

    table = ft.DataTable(
        columns=[
            ft.DataColumn(ft.Text("Name")),
            ft.DataColumn(ft.Text("Balance")),
            ft.DataColumn(ft.Text("APR")),
            ft.DataColumn(ft.Text("Min. Payment")),
            ft.DataColumn(ft.Text("Interest/mo")),
        ],
        rows=liability_rows,
        expand=True,
    )

    def on_strategy_change(e):
        strategy_state["value"] = e.control.value
        _, payoff = run_projection(strategy_state["value"])
        payoff_text.value = f"Projected payoff: {payoff or 'N/A'}"
        page.update()

    # Build content
    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Debts & Liabilities", size=24, weight=ft.FontWeight.BOLD),
                ],
            ),
            ft.Container(height=16),
            summary,
            ft.Container(height=24),
            ft.Row(
                [
                    ft.RadioGroup(
                        content=ft.Row(
                            [
                                ft.Radio(value="snowball", label="Snowball"),
                                ft.Radio(value="avalanche", label="Avalanche"),
                            ]
                        ),
                        value="snowball",
                        on_change=on_strategy_change,
                    ),
                    payoff_text,
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Card(content=ft.Container(content=table, padding=12), expand=True),
            ft.Text(
                (
                    "Strategy toggle uses the debt payoff service "
                    "(snowball/avalanche) to project payoff."
                ),
                color=ft.Colors.ON_SURFACE_VARIANT,
                size=12,
            ),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Debts", page)
    main_layout = build_main_layout(ctx, page, "/debts", content)

    return ft.View(
        route="/debts",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

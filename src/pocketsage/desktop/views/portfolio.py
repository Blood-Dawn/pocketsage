"""Portfolio view implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_portfolio_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the portfolio holdings view."""

    # Get all holdings
    holdings = ctx.holding_repo.list_all()

    # Calculate totals
    total_cost_basis = ctx.holding_repo.get_total_cost_basis()

    # Holdings table
    holding_rows = []

    for holding in holdings:
        cost_basis = holding.quantity * holding.avg_price
        # Note: We don't have current prices, so we can't calculate gain/loss
        # In a real app, you'd fetch current prices from an API

        account_name = "N/A"
        if holding.account_id:
            account = ctx.account_repo.get_by_id(holding.account_id)
            if account:
                account_name = account.name

        holding_rows.append(
            ft.Container(
                content=ft.Row(
                    [
                        ft.Text(holding.symbol, size=14, weight=ft.FontWeight.BOLD, width=100),
                        ft.Text(f"{holding.quantity:,.4f}", size=14, width=120, text_align=ft.TextAlign.RIGHT),
                        ft.Text(f"${holding.avg_price:,.2f}", size=14, width=120, text_align=ft.TextAlign.RIGHT),
                        ft.Text(f"${cost_basis:,.2f}", size=14, width=150, text_align=ft.TextAlign.RIGHT),
                        ft.Text(account_name, size=14, width=150),
                    ],
                ),
                padding=12,
                border=ft.border.only(
                    bottom=ft.border.BorderSide(1, ft.colors.OUTLINE_VARIANT)
                ),
            )
        )

    if not holding_rows:
        holdings_content = ft.Container(
            content=ft.Column(
                [
                    ft.Icon(ft.icons.TRENDING_UP_OUTLINED, size=64, color=ft.colors.ON_SURFACE_VARIANT),
                    ft.Container(height=16),
                    ft.Text(
                        "No Holdings",
                        size=20,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Container(height=8),
                    ft.Text(
                        "Add your first holding to track your portfolio",
                        size=14,
                        color=ft.colors.ON_SURFACE_VARIANT,
                    ),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            ),
            padding=40,
        )
    else:
        holdings_content = ft.Card(
            content=ft.Column(
                [
                    ft.Container(
                        content=ft.Row(
                            [
                                ft.Text("Symbol", size=14, weight=ft.FontWeight.BOLD, width=100),
                                ft.Text("Quantity", size=14, weight=ft.FontWeight.BOLD, width=120, text_align=ft.TextAlign.RIGHT),
                                ft.Text("Avg Price", size=14, weight=ft.FontWeight.BOLD, width=120, text_align=ft.TextAlign.RIGHT),
                                ft.Text("Cost Basis", size=14, weight=ft.FontWeight.BOLD, width=150, text_align=ft.TextAlign.RIGHT),
                                ft.Text("Account", size=14, weight=ft.FontWeight.BOLD, width=150),
                            ],
                        ),
                        padding=12,
                        bgcolor=ft.colors.SURFACE_VARIANT,
                    ),
                    ft.Column(holding_rows, spacing=0),
                ],
                spacing=0,
            ),
            elevation=2,
        )

    # Summary card
    summary_card = ft.Card(
        content=ft.Container(
            content=ft.Row(
                [
                    ft.Column(
                        [
                            ft.Text("Total Holdings", size=14, color=ft.colors.ON_SURFACE_VARIANT),
                            ft.Text(str(len(holdings)), size=28, weight=ft.FontWeight.BOLD),
                        ],
                    ),
                    ft.Column(
                        [
                            ft.Text("Total Cost Basis", size=14, color=ft.colors.ON_SURFACE_VARIANT),
                            ft.Text(f"${total_cost_basis:,.2f}", size=28, weight=ft.FontWeight.BOLD, color=ft.colors.PRIMARY),
                        ],
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_AROUND,
            ),
            padding=20,
        ),
        elevation=2,
    )

    # Build content
    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Portfolio", size=24, weight=ft.FontWeight.BOLD),
                ],
            ),
            ft.Container(height=16),
            summary_card,
            ft.Container(height=16),
            holdings_content,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Portfolio")
    main_layout = build_main_layout(page, "/portfolio", content)

    return ft.View(
        route="/portfolio",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

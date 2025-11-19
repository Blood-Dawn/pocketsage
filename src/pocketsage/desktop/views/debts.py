"""Debts view implementation."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_debts_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the debts/liabilities view."""

    # Get all liabilities
    liabilities = ctx.liability_repo.list_all()

    # Calculate totals
    total_debt = ctx.liability_repo.get_total_debt()
    weighted_apr = ctx.liability_repo.get_weighted_apr()
    total_min_payment = sum(liability.minimum_payment for liability in liabilities)

    # Summary cards
    summary = ft.Row(
        [
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Text("Total Debt", size=14, color=ft.colors.ON_SURFACE_VARIANT),
                            ft.Text(
                                f"${total_debt:,.2f}",
                                size=28,
                                weight=ft.FontWeight.BOLD,
                                color=ft.colors.RED,
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
                            ft.Text("Weighted APR", size=14, color=ft.colors.ON_SURFACE_VARIANT),
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
                            ft.Text("Min. Payment", size=14, color=ft.colors.ON_SURFACE_VARIANT),
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

    # Liability list
    liability_rows = []

    for liability in liabilities:
        # Calculate monthly interest
        monthly_interest = liability.balance * (liability.apr / 100) / 12

        liability_rows.append(
            ft.Card(
                content=ft.Container(
                    content=ft.Column(
                        [
                            ft.Row(
                                [
                                    ft.Text(
                                        liability.name,
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                    ),
                                    ft.Text(
                                        f"${liability.balance:,.2f}",
                                        size=18,
                                        weight=ft.FontWeight.BOLD,
                                        color=(
                                            ft.colors.RED
                                            if liability.balance > 0
                                            else ft.colors.GREEN
                                        ),
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            ),
                            ft.Container(height=12),
                            ft.Row(
                                [
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "APR", size=12, color=ft.colors.ON_SURFACE_VARIANT
                                            ),
                                            ft.Text(f"{liability.apr:.2f}%", size=14),
                                        ],
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "Min. Payment",
                                                size=12,
                                                color=ft.colors.ON_SURFACE_VARIANT,
                                            ),
                                            ft.Text(f"${liability.minimum_payment:,.2f}", size=14),
                                        ],
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "Monthly Interest",
                                                size=12,
                                                color=ft.colors.ON_SURFACE_VARIANT,
                                            ),
                                            ft.Text(
                                                f"${monthly_interest:,.2f}",
                                                size=14,
                                                color=ft.colors.ORANGE,
                                            ),
                                        ],
                                    ),
                                    ft.Column(
                                        [
                                            ft.Text(
                                                "Strategy",
                                                size=12,
                                                color=ft.colors.ON_SURFACE_VARIANT,
                                            ),
                                            ft.Text(
                                                liability.payoff_strategy.capitalize(), size=14
                                            ),
                                        ],
                                    ),
                                ],
                                alignment=ft.MainAxisAlignment.SPACE_AROUND,
                            ),
                        ],
                    ),
                    padding=20,
                ),
                elevation=1,
            )
        )

    if not liability_rows:
        liability_rows.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Icon(ft.icons.CELEBRATION, size=64, color=ft.colors.GREEN),
                        ft.Container(height=16),
                        ft.Text(
                            "Debt-Free!",
                            size=24,
                            weight=ft.FontWeight.BOLD,
                            color=ft.colors.GREEN,
                        ),
                        ft.Container(height=8),
                        ft.Text(
                            "You have no outstanding liabilities",
                            size=14,
                            color=ft.colors.ON_SURFACE_VARIANT,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                ),
                padding=40,
            )
        )

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
            ft.Column(liability_rows, spacing=16),
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Debts")
    main_layout = build_main_layout(page, "/debts", content)

    return ft.View(
        route="/debts",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

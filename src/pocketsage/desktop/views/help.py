"""Help view describing CSV formats for imports/exports."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def _code_block(text: str) -> ft.Container:
    """Render monospace code-style text for examples."""
    return ft.Container(
        content=ft.Text(text, selectable=True, font_family="monospace", size=12),
        padding=12,
        bgcolor=ft.Colors.SURFACE_CONTAINER_LOW,
        border_radius=8,
    )


def _pill(label: str) -> ft.Chip:
    return ft.Chip(label=ft.Text(label), padding=0, height=26)


def build_help_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Render CSV structure guidance for imports/exports."""

    tx_sample = "\n".join(
        [
            "date,amount,memo,category,account,currency,transaction_id",
            "2024-01-14,-42.50,Coffee,Coffee,Everyday Checking,USD,tx-123",
            "2024-01-31,1500.00,Salary,Salary,Everyday Checking,USD,pay-2024-01",
        ]
    )

    portfolio_sample = "\n".join(
        [
            "account,symbol,shares,price,as_of",
            "Brokerage,AAPL,10,189.12,2024-01-15",
            "Brokerage,VTI,5,226.35,2024-01-15",
        ]
    )

    tx_card = ft.Card(
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Transactions CSV", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Required headers: date, amount, memo, category, account. "
                        "Optional: currency (default USD) and transaction_id for de-duplication.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row(
                        [
                            _pill("date (YYYY-MM-DD)"),
                            _pill("amount (+ income / - expense)"),
                            _pill("memo"),
                            _pill("category"),
                            _pill("account"),
                            _pill("currency?"),
                        ],
                        spacing=6,
                        run_spacing=6,
                        wrap=True,
                    ),
                    ft.Text(
                        "New categories/accounts are auto-created when names are unknown. "
                        "Duplicate transaction_ids are skipped to keep imports idempotent.",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Text("Sample rows:", weight=ft.FontWeight.BOLD),
                    _code_block(tx_sample),
                ],
                spacing=10,
            ),
        )
    )

    portfolio_card = ft.Card(
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Portfolio CSV", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Use the sample layout below (also in scripts/csv_samples/portfolio.csv).",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row(
                        [
                            _pill("account"),
                            _pill("symbol"),
                            _pill("shares"),
                            _pill("price"),
                            _pill("as_of (YYYY-MM-DD)"),
                        ],
                        spacing=6,
                        wrap=True,
                        run_spacing=6,
                    ),
                    _code_block(portfolio_sample),
                ],
                spacing=10,
            ),
        )
    )

    shortcuts_card = ft.Card(
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [
                    ft.Text("Keyboard shortcuts", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        "Keep your hands on the keyboard for the actions below.",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Row(
                        [
                            ft.Text("Ctrl+N", weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "New transaction (ledger view)",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            ft.Text("Ctrl+Shift+H", weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Bring up habit entry flow",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=8,
                    ),
                    ft.Row(
                        [
                            ft.Text("Ctrl+1..7", weight=ft.FontWeight.BOLD),
                            ft.Text(
                                (
                                    "Jump between Dashboard, Ledger, Budgets, "
                                    "Habits, Debts, Portfolio, Settings"
                                ),
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
                spacing=10,
            ),
        )
    )

    content = ft.Column(
        [
            ft.Text("Help & CSV Guide", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Use these column layouts when importing data; exports follow the same shape.",
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Container(height=10),
            tx_card,
            ft.Container(height=10),
            portfolio_card,
            ft.Container(height=10),
            shortcuts_card,
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    app_bar = build_app_bar(ctx, "Help", page)
    layout = build_main_layout(ctx, page, "/help", content)

    return ft.View(route="/help", appbar=app_bar, controls=layout, padding=0)

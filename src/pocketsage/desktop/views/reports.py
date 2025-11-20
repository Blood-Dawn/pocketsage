"""Reports/export view placeholder for Flet app."""

from __future__ import annotations

import flet as ft

from ..components import build_app_bar, build_main_layout, empty_state
from ..context import AppContext


def build_reports_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the reports/export view."""

    def notify(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    cards = ft.ResponsiveRow(
        controls=[
            _report_card(
                title="Full data export",
                description="Generate ZIP with CSVs and charts.",
                on_click=lambda _: notify("Export started"),
            ),
            _report_card(
                title="Monthly spending report",
                description="Current month category breakdown.",
                on_click=lambda _: notify("Spending report queued"),
            ),
            _report_card(
                title="Year-to-date summary",
                description="Income vs expense year-to-date.",
                on_click=lambda _: notify("YTD summary queued"),
            ),
            _report_card(
                title="Debt payoff summary",
                description="Latest payoff projection as PDF/CSV.",
                on_click=lambda _: notify("Debt report queued"),
            ),
        ],
        spacing=12,
        run_spacing=12,
    )

    content = ft.Column(
        [
            ft.Text("Reports & Exports", size=24, weight=ft.FontWeight.BOLD),
            ft.Text("Generate CSVs/ZIPs for archives or sharing.", color=ft.colors.ON_SURFACE_VARIANT),
            ft.Container(height=12),
            cards,
            ft.Container(height=16),
            empty_state("More reports coming soon."),
        ],
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    app_bar = build_app_bar(ctx, "Reports", page)
    main_layout = build_main_layout(ctx, page, "/reports", content)

    return ft.View(
        route="/reports",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )


def _report_card(title: str, description: str, on_click):
    return ft.Container(
        col={"sm": 6, "md": 3},
        content=ft.Card(
            content=ft.Container(
                padding=16,
                content=ft.Column(
                    [
                        ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
                        ft.Text(description, color=ft.colors.ON_SURFACE_VARIANT, size=13),
                        ft.Container(height=8),
                        ft.FilledTonalButton("Download", icon=ft.icons.DOWNLOAD, on_click=on_click),
                    ]
                ),
            )
        ),
    )

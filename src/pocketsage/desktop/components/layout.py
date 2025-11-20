"""Layout components for the desktop app."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, List

import flet as ft

if TYPE_CHECKING:
    from ..context import AppContext


def build_app_bar(ctx: AppContext, title: str, page: ft.Page) -> ft.AppBar:
    """Build the app bar with title, month selector, and quick actions."""

    today = date.today()
    options: list[ft.dropdown.Option] = []
    for offset in (-1, 0, 1):
        month = (today.month - 1 + offset) % 12 + 1
        year = today.year + ((today.month - 1 + offset) // 12)
        label = date(year, month, 1).strftime("%b %Y")
        options.append(ft.dropdown.Option(key=f"{year}-{month:02d}", text=label))

    def set_month(e: ft.ControlEvent):
        try:
            ctx.current_month = date.fromisoformat(f"{e.control.value}-01")
        except Exception:
            pass
        page.snack_bar = ft.SnackBar(content=ft.Text(f"Switched to {e.control.value}"))
        page.snack_bar.open = True
        page.update()

    month_selector = ft.Dropdown(
        options=options,
        value=f"{today.year}-{today.month:02d}",
        width=150,
        dense=True,
        on_change=set_month,
    )

    def _go(path: str):
        page.go(path)

    quick_actions: List[ft.Control] = [
        month_selector,
        ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip="Add transaction (Ctrl+N)",
            on_click=lambda _: _go("/ledger"),
        ),
        ft.IconButton(
            icon=ft.Icons.CHECK_CIRCLE,
            tooltip="Add habit (Ctrl+Shift+H)",
            on_click=lambda _: _go("/habits"),
        ),
        ft.IconButton(
            icon=ft.Icons.DOWNLOAD,
            tooltip="Run demo seed",
            on_click=lambda _: _run_seed(ctx, page),
        ),
    ]

    return ft.AppBar(
        leading=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET),
        title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=quick_actions,
    )


def _run_seed(ctx: AppContext, page: ft.Page) -> None:
    """Trigger demo seed and notify user."""
    try:
        from pocketsage.services.admin_tasks import run_demo_seed

        run_demo_seed(session_factory=ctx.session_factory)
        page.snack_bar = ft.SnackBar(content=ft.Text("Demo data seeded"))
    except Exception as exc:  # pragma: no cover - surface friendly error
        page.snack_bar = ft.SnackBar(content=ft.Text(f"Seed failed: {exc}"))
    page.snack_bar.open = True
    page.update()


def build_navigation_rail(page: ft.Page, current_route: str) -> ft.NavigationRail:
    """Build the navigation rail with route selection."""

    routes = [
        "/dashboard",
        "/ledger",
        "/budgets",
        "/habits",
        "/debts",
        "/portfolio",
        "/reports",
        "/help",
        "/settings",
    ]

    def route_changed(e):
        """Handle navigation selection."""
        selected_idx = e.control.selected_index
        if 0 <= selected_idx < len(routes):
            page.go(routes[selected_idx])

    try:
        selected_index = routes.index(current_route)
    except ValueError:
        selected_index = 0

    return ft.NavigationRail(
        selected_index=selected_index,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=ft.Icons.DASHBOARD_OUTLINED,
                selected_icon=ft.Icons.DASHBOARD,
                label="Dashboard",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.RECEIPT_LONG_OUTLINED,
                selected_icon=ft.Icons.RECEIPT_LONG,
                label="Ledger",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ACCOUNT_BALANCE_OUTLINED,
                selected_icon=ft.Icons.ACCOUNT_BALANCE,
                label="Budgets",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.CHECK_CIRCLE_OUTLINE,
                selected_icon=ft.Icons.CHECK_CIRCLE,
                label="Habits",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.CREDIT_CARD_OUTLINED,
                selected_icon=ft.Icons.CREDIT_CARD,
                label="Debts",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.TRENDING_UP_OUTLINED,
                selected_icon=ft.Icons.TRENDING_UP,
                label="Portfolio",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.ASSESSMENT_OUTLINED,
                selected_icon=ft.Icons.ASSESSMENT,
                label="Reports",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.HELP_OUTLINE,
                selected_icon=ft.Icons.HELP,
                label="Help",
            ),
            ft.NavigationRailDestination(
                icon=ft.Icons.SETTINGS_OUTLINED,
                selected_icon=ft.Icons.SETTINGS,
                label="Settings",
            ),
        ],
        on_change=route_changed,
    )


def build_main_layout(
    ctx: AppContext,
    page: ft.Page,
    current_route: str,
    content: ft.Control,
) -> List[ft.Control]:
    """Build the main layout with navigation rail, content, and status bar."""

    nav_rail = build_navigation_rail(page, current_route)

    status = ft.Container(
        content=ft.Row(
            [
                ft.Text(f"DB: {ctx.config.DATABASE_URL}", size=11, overflow=ft.TextOverflow.ELLIPSIS),
                ft.Text(f"Encryption: {'on' if ctx.config.USE_SQLCIPHER else 'off'}", size=11),
                ft.Text(f"Month: {ctx.current_month.strftime('%b %Y')}", size=11),
            ],
            spacing=12,
        ),
        padding=ft.padding.symmetric(vertical=8, horizontal=12),
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
    )

    return [
        ft.Row(
            [
                nav_rail,
                ft.VerticalDivider(width=1),
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Container(content=content, expand=True, padding=20),
                            status,
                        ],
                        spacing=0,
                        expand=True,
                    ),
                    expand=True,
                ),
            ],
            spacing=0,
            expand=True,
        )
    ]

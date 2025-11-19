"""Layout components for the desktop app."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

import flet as ft

if TYPE_CHECKING:
    from ..context import AppContext


def build_app_bar(ctx: AppContext, title: str, actions: List[ft.Control] = None) -> ft.AppBar:
    """Build the app bar with title and optional actions."""
    if actions is None:
        actions = []

    return ft.AppBar(
        leading=ft.Icon(ft.icons.ACCOUNT_BALANCE_WALLET),
        title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.colors.SURFACE_VARIANT,
        actions=actions,
    )


def build_navigation_rail(page: ft.Page, current_route: str) -> ft.NavigationRail:
    """Build the navigation rail with route selection."""

    def route_changed(e):
        """Handle navigation selection."""
        destinations = [
            "/dashboard",
            "/ledger",
            "/budgets",
            "/habits",
            "/debts",
            "/portfolio",
            "/settings",
        ]
        selected_idx = e.control.selected_index
        if 0 <= selected_idx < len(destinations):
            page.go(destinations[selected_idx])

    # Find current index
    routes = [
        "/dashboard",
        "/ledger",
        "/budgets",
        "/habits",
        "/debts",
        "/portfolio",
        "/settings",
    ]
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
                icon=ft.icons.DASHBOARD_OUTLINED,
                selected_icon=ft.icons.DASHBOARD,
                label="Dashboard",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.RECEIPT_LONG_OUTLINED,
                selected_icon=ft.icons.RECEIPT_LONG,
                label="Ledger",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.ACCOUNT_BALANCE_OUTLINED,
                selected_icon=ft.icons.ACCOUNT_BALANCE,
                label="Budgets",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.CHECK_CIRCLE_OUTLINE,
                selected_icon=ft.icons.CHECK_CIRCLE,
                label="Habits",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.CREDIT_CARD_OUTLINED,
                selected_icon=ft.icons.CREDIT_CARD,
                label="Debts",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.TRENDING_UP_OUTLINED,
                selected_icon=ft.icons.TRENDING_UP,
                label="Portfolio",
            ),
            ft.NavigationRailDestination(
                icon=ft.icons.SETTINGS_OUTLINED,
                selected_icon=ft.icons.SETTINGS,
                label="Settings",
            ),
        ],
        on_change=route_changed,
    )


def build_main_layout(
    page: ft.Page,
    current_route: str,
    content: ft.Control,
) -> List[ft.Control]:
    """Build the main layout with navigation rail and content."""

    nav_rail = build_navigation_rail(page, current_route)

    return [
        ft.Row(
            [
                nav_rail,
                ft.VerticalDivider(width=1),
                ft.Container(
                    content=content,
                    expand=True,
                    padding=20,
                ),
            ],
            spacing=0,
            expand=True,
        )
    ]

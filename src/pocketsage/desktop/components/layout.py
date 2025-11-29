"""Layout components for the desktop app."""

from __future__ import annotations

from typing import TYPE_CHECKING, List

import flet as ft

if TYPE_CHECKING:
    from ..context import AppContext

from .. import controllers
from ..navigation_helpers import NAVIGATION_DESTINATIONS, index_for_route


def build_app_bar(ctx: AppContext, title: str, page: ft.Page) -> ft.AppBar:
    """Build the app bar with quick actions (no global month picker)."""

    def _go(path: str):
        controllers.navigate(page, path)

    def _logout(_e):
        ctx.current_user = None
        ctx.guest_mode = False
        ctx.admin_mode = False
        page.snack_bar = ft.SnackBar(content=ft.Text("Logged out successfully"))
        page.snack_bar.open = True
        page.go("/login")

    def _refresh(_e):
        """Refresh the current view."""
        current_route = getattr(page, "route", "/dashboard")
        page.snack_bar = ft.SnackBar(content=ft.Text("Refreshing..."))
        page.snack_bar.open = True
        # Trigger rerender by re-navigating to the current route.
        page.go(current_route)
        page.update()

    quick_actions: List[ft.Control] = [
        ft.IconButton(
            icon=ft.Icons.ADD,
            tooltip="Add transaction (Ctrl+N)",
            on_click=lambda _: _go("/add-data"),
        ),
        ft.IconButton(
            icon=ft.Icons.CHECK_CIRCLE,
            tooltip="Add habit (Ctrl+Shift+H)",
            on_click=lambda _: _go("/add-data"),
        ),
    ]
    if ctx.current_user:
        user_role = ctx.current_user.role or "user"
        user_chip_label = f"{ctx.current_user.username} ({user_role})"
        quick_actions.extend([
            ft.Chip(
                label=ft.Text(user_chip_label),
                leading=ft.Icon(ft.Icons.PERSON),
            ),
            ft.IconButton(
                icon=ft.Icons.LOGOUT,
                tooltip="Logout",
                on_click=_logout,
            ),
        ])

    return ft.AppBar(
        leading=ft.Icon(ft.Icons.ACCOUNT_BALANCE_WALLET),
        title=ft.Text(title, size=20, weight=ft.FontWeight.BOLD),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        actions=quick_actions,
    )


def build_navigation_rail(ctx: AppContext, page: ft.Page, current_route: str) -> ft.NavigationRail:
    """Build the navigation rail with route selection."""

    def route_changed(e):
        """Keep navigation logic isolated in helpers."""
        controllers.handle_nav_selection(ctx, page, e.control.selected_index)

    is_admin = ctx.current_user and ctx.current_user.role == "admin"
    selected_index = index_for_route(current_route, is_admin=is_admin)
    destinations = [dest for dest in NAVIGATION_DESTINATIONS if is_admin or dest.route != "/admin"]

    return ft.NavigationRail(
        selected_index=selected_index,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        destinations=[
            ft.NavigationRailDestination(
                icon=dest.icon,
                selected_icon=dest.selected_icon,
                label=dest.label,
            )
            for dest in destinations
        ],
        on_change=route_changed,
    )


def build_main_layout(
    ctx: AppContext,
    page: ft.Page,
    current_route: str,
    content: ft.Control,
    use_menu_bar: bool = False,
) -> List[ft.Control]:
    """Build the main layout with navigation rail and content.

    Args:
        ctx: Application context
        page: Flet page
        current_route: Current route path
        content: Main content control
        use_menu_bar: If True, use HomeBank-style menu bar instead of navigation rail

    Returns:
        List of controls to display
    """
    if use_menu_bar:
        # HomeBank-style: menu bar at top, full-width content below
        from .menubar import build_menu_bar
        menu = build_menu_bar(ctx, page)

        content_column = ft.Column(
            [
                ft.Container(content=content, expand=True, padding=20),
            ],
            spacing=0,
            expand=True,
        )

        return [
            ft.Column(
                [
                    menu,
                    ft.Divider(height=1, thickness=1),
                    ft.Container(
                        content=content_column,
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            )
        ]
    else:
        # Original navigation rail layout
        nav_rail = build_navigation_rail(ctx, page, current_route)

        content_column = ft.Column(
            [
                ft.Container(content=content, expand=True, padding=20),
            ],
            spacing=0,
            expand=True,
        )

        return [
            ft.Row(
                [
                    nav_rail,
                    ft.VerticalDivider(width=1),
                    ft.Container(
                        content=content_column,
                        expand=True,
                    ),
                ],
                spacing=0,
                expand=True,
            )
        ]

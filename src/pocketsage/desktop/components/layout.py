"""Layout components for the desktop app."""

from __future__ import annotations

from contextlib import suppress
from datetime import date
from typing import TYPE_CHECKING, List

import flet as ft

if TYPE_CHECKING:
    from ..context import AppContext

from .. import controllers
from ..navigation_helpers import NAVIGATION_DESTINATIONS, index_for_route


def build_app_bar(ctx: AppContext, title: str, page: ft.Page) -> ft.AppBar:
    """Build the app bar with title, month selector, and quick actions."""

    today = date.today()
    base_month = (getattr(ctx, "current_month", None) or today).replace(day=1)
    options: list[ft.dropdown.Option] = []
    for offset in (-1, 0, 1):
        month = (base_month.month - 1 + offset) % 12 + 1
        year = base_month.year + ((base_month.month - 1 + offset) // 12)
        label = date(year, month, 1).strftime("%b %Y")
        options.append(ft.dropdown.Option(key=f"{year}-{month:02d}", text=label))

    def set_month(e: ft.ControlEvent):
        with suppress(Exception):
            ctx.current_month = date.fromisoformat(f"{e.control.value}-01")
        page.snack_bar = ft.SnackBar(content=ft.Text(f"Switched to {e.control.value}"))
        page.snack_bar.open = True
        # Refresh month-aware views inline so the change is visible immediately.
        current_route = getattr(page, "route", "")
        if current_route in {"/budgets", "/reports"}:
            page.go(current_route)
        page.update()

    month_selector = ft.Dropdown(
        options=options,
        value=f"{base_month.year}-{base_month.month:02d}",
        width=150,
        dense=True,
        on_change=set_month,
    )

    def _go(path: str):
        controllers.navigate(page, path)

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
    ]
    if ctx.current_user:
        user_chip_label = ctx.current_user.username or "Guest"
        quick_actions.append(
            ft.Chip(
                label=ft.Text(f"{user_chip_label} - Offline"),
                leading=ft.Icon(ft.Icons.PERSON),
            )
        )

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

    is_admin = ctx.current_user is not None and ctx.current_user.role == "admin"
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
) -> List[ft.Control]:
    """Build the main layout with navigation rail and content."""

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

"""Navigation metadata and helpers for the desktop app."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Protocol

import flet as ft


class PageLike(Protocol):
    """Minimal subset of `ft.Page` needed for navigation helpers."""

    def go(self, route: str) -> None: ...


@dataclass(frozen=True)
class NavigationDestination:
    """Metadata for a desktop navigation rail entry."""

    route: str
    label: str
    icon: str
    selected_icon: str


NAVIGATION_DESTINATIONS: List[NavigationDestination] = [
    NavigationDestination(
        "/dashboard",
        "Dashboard",
        ft.Icons.DASHBOARD_OUTLINED,
        ft.Icons.DASHBOARD,
    ),
    NavigationDestination(
        "/ledger",
        "Ledger",
        ft.Icons.RECEIPT_LONG_OUTLINED,
        ft.Icons.RECEIPT_LONG,
    ),
    NavigationDestination(
        "/budgets",
        "Budgets",
        ft.Icons.ACCOUNT_BALANCE_OUTLINED,
        ft.Icons.ACCOUNT_BALANCE,
    ),
    NavigationDestination(
        "/habits",
        "Habits",
        ft.Icons.CHECK_CIRCLE_OUTLINE,
        ft.Icons.CHECK_CIRCLE,
    ),
    NavigationDestination(
        "/debts",
        "Debts",
        ft.Icons.CREDIT_CARD_OUTLINED,
        ft.Icons.CREDIT_CARD,
    ),
    NavigationDestination(
        "/portfolio",
        "Portfolio",
        ft.Icons.TRENDING_UP_OUTLINED,
        ft.Icons.TRENDING_UP,
    ),
    NavigationDestination(
        "/reports",
        "Reports",
        ft.Icons.ASSESSMENT_OUTLINED,
        ft.Icons.ASSESSMENT,
    ),
    NavigationDestination(
        "/help",
        "Help",
        ft.Icons.HELP_OUTLINE,
        ft.Icons.HELP,
    ),
    NavigationDestination(
        "/settings",
        "Settings",
        ft.Icons.SETTINGS_OUTLINED,
        ft.Icons.SETTINGS,
    ),
    NavigationDestination(
        "/admin",
        "Admin",
        ft.Icons.ADMIN_PANEL_SETTINGS_OUTLINED,
        ft.Icons.ADMIN_PANEL_SETTINGS,
    ),
]


_SHORTCUT_DIGIT_ROUTES = {
    "1": "/dashboard",
    "2": "/ledger",
    "3": "/budgets",
    "4": "/habits",
    "5": "/debts",
    "6": "/portfolio",
    "7": "/settings",
}


_SHORTCUT_KEYS_WITH_CTRL = {
    "n": "/ledger",
}


def _filter_destinations(is_admin: bool) -> list[NavigationDestination]:
    """Filter navigation destinations based on role."""
    if is_admin:
        return NAVIGATION_DESTINATIONS
    return [dest for dest in NAVIGATION_DESTINATIONS if dest.route != "/admin"]


def nav_routes(is_admin: bool = False) -> list[str]:
    """List of routes represented in the navigation rail."""
    return [dest.route for dest in _filter_destinations(is_admin)]


def route_for_index(selected_index: int, *, is_admin: bool = False) -> Optional[str]:
    """Return the route that corresponds to the selected navigation index."""
    destinations = _filter_destinations(is_admin)
    if 0 <= selected_index < len(destinations):
        return destinations[selected_index].route
    return None


def index_for_route(route: str, *, is_admin: bool = False) -> int:
    """Return the index of the destination matching the requested route."""
    try:
        return nav_routes(is_admin).index(route)
    except ValueError:
        return 0


def handle_navigation_selection(
    page: PageLike, selected_index: int, *, is_admin: bool = False
) -> None:
    """Go to the route that was selected in the navigation rail."""
    if route := route_for_index(selected_index, is_admin=is_admin):
        page.go(route)


def resolve_shortcut_route(key: str, ctrl: bool, shift: bool) -> Optional[str]:
    """Map keyboard shortcuts to navigation routes."""
    key = (key or "").lower()
    if ctrl and shift and key == "h":
        return "/habits"
    if ctrl and not shift:
        if key in _SHORTCUT_DIGIT_ROUTES:
            return _SHORTCUT_DIGIT_ROUTES[key]
        return _SHORTCUT_KEYS_WITH_CTRL.get(key)
    return None


__all__ = [
    "NavigationDestination",
    "NAVIGATION_DESTINATIONS",
    "handle_navigation_selection",
    "index_for_route",
    "nav_routes",
    "resolve_shortcut_route",
    "route_for_index",
]

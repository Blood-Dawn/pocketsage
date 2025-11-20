"""Main Flet desktop application entry point."""

from __future__ import annotations

import flet as ft

from .context import create_app_context
from .navigation import Router
from .views.budgets import build_budgets_view
from .views.dashboard import build_dashboard_view
from .views.debts import build_debts_view
from .views.habits import build_habits_view
from .views.ledger import build_ledger_view
from .views.portfolio import build_portfolio_view
from .views.reports import build_reports_view
from .views.help import build_help_view
from .views.settings import build_settings_view


def main(page: ft.Page) -> None:
    """Main entry point for the Flet desktop app."""

    # Configure page
    page.title = "PocketSage"
    page.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window_width = 1280
    page.window_height = 800
    page.window_min_width = 1024
    page.window_min_height = 600

    # Create app context
    ctx = create_app_context()
    ctx.page = page

    # Create router
    router = Router(page, ctx)

    # Register routes
    router.register("/dashboard", build_dashboard_view)
    router.register("/", build_dashboard_view)
    router.register("/ledger", build_ledger_view)
    router.register("/budgets", build_budgets_view)
    router.register("/habits", build_habits_view)
    router.register("/debts", build_debts_view)
    router.register("/portfolio", build_portfolio_view)
    router.register("/reports", build_reports_view)
    router.register("/help", build_help_view)
    router.register("/settings", build_settings_view)

    # Set up event handlers
    page.on_route_change = router.route_change
    page.on_view_pop = router.view_pop

    def handle_shortcuts(e: ft.KeyboardEvent):
        """Global keyboard shortcuts for navigation/quick actions."""
        key = (e.key or "").lower()
        if e.ctrl and not e.shift and key == "n":
            page.go("/ledger")
        elif e.ctrl and e.shift and key == "h":
            page.go("/habits")
        elif e.ctrl and key in {"1", "2", "3", "4", "5", "6", "7"}:
            routes = {
                "1": "/dashboard",
                "2": "/ledger",
                "3": "/budgets",
                "4": "/habits",
                "5": "/debts",
                "6": "/portfolio",
                "7": "/settings",
            }
            page.go(routes[key])

    page.on_keyboard_event = handle_shortcuts

    # Navigate to default route
    page.go("/dashboard")


if __name__ == "__main__":
    ft.app(target=main)

"""Main Flet desktop application entry point."""

from __future__ import annotations

import flet as ft

from . import controllers
from .context import create_app_context
from ..devtools import dev_log
from .navigation import Router
from .views.admin import build_admin_view
from .views.auth import build_auth_view
from .views.budgets import build_budgets_view
from .views.dashboard import build_dashboard_view
from .views.debts import build_debts_view
from .views.habits import build_habits_view
from .views.help import build_help_view
from .views.ledger import build_ledger_view
from .views.portfolio import build_portfolio_view
from .views.reports import build_reports_view
from .views.settings import build_settings_view


def main(page: ft.Page) -> None:
    """Main entry point for the Flet desktop app."""

    # Configure page
    # Create app context (needs config)
    ctx = create_app_context()
    ctx.page = page
    page.title = "PocketSage (DEV)" if ctx.dev_mode else "PocketSage"
    if ctx.dev_mode:
        dev_log(ctx.config, "Dev mode enabled", context={"data_dir": ctx.config.DATA_DIR})
        page.banner = ft.Banner(
            bgcolor=ft.Colors.AMBER_50,
            leading=ft.Icon(ft.Icons.BUG_REPORT, color=ft.Colors.AMBER_700),
            content=ft.Text("Developer mode: errors will be printed to the console."),
            actions=[ft.TextButton("Hide", on_click=lambda e: setattr(page.banner, "open", False))],
            open=True,
        )
    # Theme preference
    persisted_theme = ctx.settings_repo.get("theme_mode")
    if persisted_theme and persisted_theme.value.lower() == "light":
        page.theme_mode = ft.ThemeMode.LIGHT
        ctx.theme_mode = ft.ThemeMode.LIGHT
    else:
        page.theme_mode = ft.ThemeMode.DARK
        ctx.theme_mode = ft.ThemeMode.DARK
    page.padding = 0
    page.window_width = 1280
    page.window_height = 800
    page.window_min_width = 1024
    page.window_min_height = 600
    transitions = ft.PageTransitionsTheme(
        android=ft.PageTransitionTheme.NONE,
        ios=ft.PageTransitionTheme.NONE,
        macos=ft.PageTransitionTheme.NONE,
        windows=ft.PageTransitionTheme.NONE,
    )
    page.theme = ft.Theme(page_transitions=transitions)
    page.dark_theme = ft.Theme(page_transitions=transitions)

    # Shared file picker overlay for imports
    controllers.attach_file_picker(ctx, page)

    # Create router
    router = Router(page, ctx)

    # Register routes and aliases
    route_builders = {
        "/login": build_auth_view,
        "/dashboard": build_dashboard_view,
        "/": build_dashboard_view,
        "/ledger": build_ledger_view,
        "/budgets": build_budgets_view,
        "/habits": build_habits_view,
        "/debts": build_debts_view,
        "/portfolio": build_portfolio_view,
        "/reports": build_reports_view,
        "/help": build_help_view,
        "/settings": build_settings_view,
        "/admin": build_admin_view,
    }
    for route, builder in route_builders.items():
        router.register(route, builder)

    # Set up event handlers
    page.on_route_change = router.route_change
    page.on_view_pop = router.view_pop

    def handle_shortcuts(e: ft.KeyboardEvent):
        """Global keyboard shortcuts for quick navigation."""
        controllers.handle_shortcut(page, e.key, e.ctrl, e.shift)

    page.on_keyboard_event = handle_shortcuts

    # TODO(@codex): Skip login and go directly to dashboard for guest mode MVP
    #    - No authentication required; user is automatically logged in as guest
    #    - This provides immediate access to the app without login screens
    # Navigate to default route
    page.go("/dashboard")


if __name__ == "__main__":
    ft.app(target=main)

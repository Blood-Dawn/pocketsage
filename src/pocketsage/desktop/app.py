"""Main Flet desktop application entry point."""

from __future__ import annotations

import time
from pathlib import Path

import flet as ft

from ..devtools import dev_log
from ..logging_config import setup_logging
from ..scheduler import create_scheduler
from . import controllers
from .context import create_app_context
from .navigation import Router
from .views.add_data import build_add_data_view
from .views.admin import build_admin_view
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

    # Initialize structured logging
    logger = setup_logging(ctx.config)
    logger.info("PocketSage desktop application starting")

    # Initialize background scheduler for periodic tasks
    scheduler = create_scheduler(ctx, auto_start=True)

    # Cleanup on page close
    def on_page_close(_):
        logger.info("Application closing, shutting down scheduler")
        scheduler.stop()
        # Export session log location for user reference
        from ..logging_config import session_log_path
        slp = session_log_path()
        if slp:
            logger.info(f"Debug session log saved to: {slp}")
            print(f"\n=== Debug log saved to: {slp} ===\n")

    page.on_close = on_page_close

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
    saved_mode = (persisted_theme.value if persisted_theme else "").strip().lower()
    if saved_mode == "light":
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
    from .views.auth import build_auth_view
    from .views.about import build_about_view

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
        "/about": build_about_view,
        "/settings": build_settings_view,
        "/admin": build_admin_view,
        "/add-data": build_add_data_view,
    }
    for route, builder in route_builders.items():
        router.register(route, builder)

    # Set up event handlers
    page.on_route_change = router.route_change
    page.on_view_pop = router.view_pop

    # Capture flet page errors into logger
    # Throttle repeated identical Flet error events (they can spam thousands of times in <1s)
    _last_err_msg: str | None = None
    _last_err_ts: float = 0.0
    _suppress_count: int = 0
    _error_log: list[str] = []
    _session_log_path: Path | None = None

    def _on_error(e: ft.ControlEvent):  # pragma: no cover (UI callback)
        nonlocal _last_err_msg, _last_err_ts, _suppress_count, _error_log, _session_log_path
        msg = getattr(e, 'data', None) or "<no-data>"
        _error_log.append(msg)
        now = time.time()
        # If same message within 0.5s, suppress
        if _last_err_msg == msg and (now - _last_err_ts) < 0.5:
            _suppress_count += 1
            _last_err_ts = now
            # Log a summary every 100 suppressed repeats to retain visibility without flooding
            if _suppress_count % 100 == 0:
                logger.warning(
                    "Repeated Flet errors suppressed",
                    extra={"event": "error_suppressed", "error_message": msg, "suppressed": _suppress_count},
                )
            return
        # New message or spaced out
        if _suppress_count:
            logger.warning(
                "Suppression summary",
                extra={"event": "error_suppression_summary", "error_message": _last_err_msg, "suppressed": _suppress_count},
            )
        _last_err_msg = msg
        _last_err_ts = now
        _suppress_count = 0
        logger.error("Flet page error", extra={"event": "error", "data": msg, "errors": _error_log[-5:]})
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"UI error: {msg}"),
            action="Open log",
            on_action=lambda _: page.launch_url(str((_session_log_path or (Path(ctx.config.DATA_DIR) / 'logs' / 'session.log')).as_posix()))
            if hasattr(page, "launch_url")
            else None,
        )
        page.snack_bar.open = True
        page.update()

    page.on_error = _on_error

    def handle_shortcuts(e: ft.KeyboardEvent):
        """Global keyboard shortcuts for quick navigation."""
        controllers.handle_shortcut(page, e.key, e.ctrl, e.shift)

    page.on_keyboard_event = handle_shortcuts

    # Start at login screen
    page.go("/login")


if __name__ == "__main__":
    ft.app(target=main)

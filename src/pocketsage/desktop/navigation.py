"""Navigation and routing for Flet desktop app."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict

import flet as ft

if TYPE_CHECKING:
    from .context import AppContext

from ..devtools import dev_log
from ..logging_config import get_logger

logger = get_logger(__name__)

# View builder type
ViewBuilder = Callable[["AppContext", ft.Page], ft.View]


class Router:
    """Handles routing and navigation for the Flet app."""

    def __init__(self, page: ft.Page, context: AppContext):
        """Initialize router with page and context."""
        self.page = page
        self.context = context
        self.routes: Dict[str, ViewBuilder] = {}

    def register(self, route: str, builder) -> None:
        """Register a route with its view builder."""
        logger.debug(f"Registering route: {route}")
        self.routes[route] = builder

    def route_change(self, e: ft.RouteChangeEvent) -> None:
        """Handle route change events."""
        route = e.route or "/"
        is_admin = (self.context.current_user and self.context.current_user.role == "admin") or bool(
            getattr(self.context, "admin_mode", False)
        )
        logger.info(f"Route change requested: {route}", extra={"user": self.context.current_user.username if self.context.current_user else None, "role": self.context.current_user.role if self.context.current_user else None})

        # Require login for all routes except /login
        if route != "/login" and self.context.current_user is None:
            logger.warning("Route blocked - user not logged in")
            self.page.go("/login")
            return

        if route == "/admin" and not is_admin:
            logger.warning("Admin route blocked - user does not have admin role")
            self.show_error("Admin access required. Please log in with an admin account.")
            route = "/dashboard"

        if route not in self.routes:
            logger.warning(f"Route not in registered routes: {route}, defaulting to dashboard")
            route = "/dashboard"

        builder = self.routes.get(route)
        if not builder:
            logger.error(f"No builder found for route: {route}")
            self.page.go("/dashboard")
            return

        try:
            logger.debug(f"Building view for route: {route}")
            view = builder(self.context, self.page)
            if self.page.views:
                self.page.views[-1] = view
            else:
                self.page.views.append(view)
            self.page.update()
            logger.info(f"Successfully loaded view for route: {route}")
        except Exception as ex:
            logger.error(f"Failed to build view for route {route}: {ex}", exc_info=True)
            dev_log(self.context.config, "Route load failed", exc=ex, context={"route": route})
            self.show_error(f"Error loading view: {ex}")

    def view_pop(self, e: ft.ViewPopEvent) -> None:
        """Handle back button navigation."""
        self.page.views.pop()
        top_view = self.page.views[-1]
        self.page.go(top_view.route)

    def show_error(self, message: str) -> None:
        """Display an error dialog."""
        dialog = ft.AlertDialog(
            title=ft.Text("Error"),
            content=ft.Text(message),
            actions=[ft.TextButton("OK", on_click=lambda _: self.close_dialog(dialog))],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def close_dialog(self, dialog: ft.AlertDialog) -> None:
        """Close a dialog."""
        dialog.open = False
        self.page.update()

"""Navigation and routing for Flet desktop app."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict

import flet as ft

if TYPE_CHECKING:
    from .context import AppContext

from ..devtools import dev_log


# View builder type
ViewBuilder = Callable[["AppContext", ft.Page], ft.View]


class Router:
    """Handles routing and navigation for the Flet app."""

    def __init__(self, page: ft.Page, context: AppContext):
        """Initialize router with page and context."""
        self.page = page
        self.context = context
        self.routes: Dict[str, ViewBuilder] = {}

    def register(self, route: str, builder: ViewBuilder) -> None:
        """Register a route with its view builder."""
        self.routes[route] = builder

    def route_change(self, e: ft.RouteChangeEvent) -> None:
        """Handle route change events."""
        route = e.route or "/"
        if route == "/login":
            route = "/dashboard"
        if route == "/admin" and not getattr(self.context, "admin_mode", False):
            self.show_error("Enable Admin mode to access admin tools.")
            route = "/dashboard"

        if route not in self.routes:
            route = "/dashboard"

        builder = self.routes.get(route)
        if not builder:
            self.page.go("/dashboard")
            return

        try:
            view = builder(self.context, self.page)
            if self.page.views:
                self.page.views[-1] = view
            else:
                self.page.views.append(view)
            self.page.update()
        except Exception as ex:
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

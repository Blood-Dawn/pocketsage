"""Navigation and routing for Flet desktop app."""

from __future__ import annotations

from typing import TYPE_CHECKING, Callable, Dict

import flet as ft

if TYPE_CHECKING:
    from .context import AppContext


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
        route = e.route

        # Find matching route
        builder = self.routes.get(route)

        if builder:
            try:
                # Build view
                view = builder(self.context, self.page)

                # Clear existing views
                self.page.views.clear()

                # Add new view
                self.page.views.append(view)

                # Update page
                self.page.update()
            except Exception as ex:
                # Show error dialog
                self.show_error(f"Error loading view: {ex}")
        else:
            # Unknown route, redirect to dashboard
            self.page.go("/dashboard")

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
            actions=[
                ft.TextButton("OK", on_click=lambda _: self.close_dialog(dialog))
            ],
        )
        self.page.dialog = dialog
        dialog.open = True
        self.page.update()

    def close_dialog(self, dialog: ft.AlertDialog) -> None:
        """Close a dialog."""
        dialog.open = False
        self.page.update()

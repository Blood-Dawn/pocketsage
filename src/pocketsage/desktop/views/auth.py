"""Authentication view placeholder (bypassed for login-free desktop mode)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ...services import auth

if TYPE_CHECKING:  # pragma: no cover
    from ..context import AppContext


def build_auth_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Immediately redirect to the dashboard in login-free mode."""

    if ctx.current_user is None:
        try:
            ctx.current_user = auth.ensure_local_user(ctx.session_factory)
            ctx.guest_mode = False
            ctx.admin_mode = False
        except Exception:
            pass

    page.go("/dashboard")
    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=ft.Text("Login is disabled; redirecting to dashboard."),
                padding=20,
            )
        ],
        padding=0,
    )

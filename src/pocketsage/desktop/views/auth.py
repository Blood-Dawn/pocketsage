"""Authentication view for user login."""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ...services import auth

if TYPE_CHECKING:  # pragma: no cover
    from ..context import AppContext


def build_auth_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build login view with username and password fields."""

    # If already logged in, redirect to dashboard
    if ctx.current_user is not None:
        page.go("/dashboard")
        return ft.View(
            route="/login",
            controls=[ft.Container(content=ft.Text("Redirecting..."), padding=20)],
            padding=0,
        )

    username_field = ft.TextField(
        label="Username",
        hint_text="Enter username (admin or local)",
        autofocus=True,
        width=300,
    )
    password_field = ft.TextField(
        label="Password",
        hint_text="Enter password",
        password=True,
        can_reveal_password=True,
        width=300,
    )
    error_text = ft.Text("", color=ft.Colors.ERROR, visible=False)

    def do_login(_e):
        error_text.visible = False
        username = username_field.value or ""
        password = password_field.value or ""

        if not username or not password:
            error_text.value = "Username and password are required"
            error_text.visible = True
            page.update()
            return

        user = auth.authenticate(
            username=username,
            password=password,
            session_factory=ctx.session_factory,
        )

        if user is None:
            error_text.value = "Invalid username or password"
            error_text.visible = True
            page.update()
            return

        ctx.current_user = user
        ctx.guest_mode = False
        page.snack_bar = ft.SnackBar(
            content=ft.Text(f"Welcome, {user.username}!")
        )
        page.snack_bar.open = True
        page.go("/dashboard")

    def on_key_press(e: ft.KeyboardEvent):
        if e.key == "Enter":
            do_login(e)

    username_field.on_submit = lambda _: password_field.focus()
    password_field.on_submit = do_login

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                content=ft.Column(
                    controls=[
                        ft.Container(
                            content=ft.Icon(
                                ft.Icons.ACCOUNT_BALANCE_WALLET,
                                size=64,
                                color=ft.Colors.PRIMARY,
                            ),
                            alignment=ft.alignment.center,
                        ),
                        ft.Text(
                            "PocketSage",
                            size=32,
                            weight=ft.FontWeight.BOLD,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Sign in to continue",
                            size=16,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Container(height=32),
                        username_field,
                        password_field,
                        error_text,
                        ft.Container(height=16),
                        ft.FilledButton(
                            "Sign In",
                            width=300,
                            on_click=do_login,
                        ),
                        ft.Container(height=16),
                        ft.Text(
                            "Default accounts:",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Admin: admin / admin123",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                        ft.Text(
                            "Local: local / local123",
                            size=12,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            text_align=ft.TextAlign.CENTER,
                        ),
                    ],
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=8,
                ),
                alignment=ft.alignment.center,
                expand=True,
            )
        ],
        padding=20,
    )

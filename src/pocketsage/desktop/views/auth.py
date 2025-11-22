"""Authentication and onboarding view for the desktop app."""

# TODO(@codex): Login view bypassed for login-free MVP
#    - This view is no longer used in the default flow (app starts in guest mode)
#    - Kept for future multi-user functionality when auth is re-enabled
#    - For now, accessing /login will redirect to dashboard automatically

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from datetime import date

from ...services import admin_tasks, auth

if TYPE_CHECKING:  # pragma: no cover
    from ..context import AppContext


def build_auth_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Render login/onboarding screen."""

    # TODO(@codex): Always redirect to dashboard in login-free MVP
    #    - Guest user is auto-created on app startup
    #    - No need to show login screen for single-user offline app
    # Redirect if already authenticated (or in guest mode)
    if ctx.current_user is not None or ctx.guest_mode:
        page.go("/dashboard")
        return ft.View(route="/login", controls=[], padding=0)

    try:
        auth.purge_guest_user(ctx.session_factory)
    except Exception:
        pass
    users_exist = auth.any_users_exist(ctx.session_factory)
    status_text = ft.Ref[ft.Text]()

    username = ft.TextField(label="Username", autofocus=True, width=280)
    password = ft.TextField(label="Password", password=True, can_reveal_password=True, width=280)

    new_username = ft.TextField(label="New username", width=280)
    new_password = ft.TextField(
        label="Password", password=True, can_reveal_password=True, width=280
    )
    confirm_password = ft.TextField(
        label="Confirm password", password=True, can_reveal_password=True, width=280
    )
    first_admin = ft.Checkbox(label="Create as admin", value=not users_exist and True)

    def _show_message(message: str) -> None:
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()
        if status_text.current:
            status_text.current.value = message
            status_text.current.update()

    def _ensure_seed(user_id: int) -> None:
        """Seed per-user demo data the first time a user signs in."""

        # Keep login fast; only seed when explicitly requested via admin/settings.
        ctx.current_month = date.today().replace(day=1)
        ctx.current_account_id = None

    def handle_login(_):
        if not username.value or not password.value:
            _show_message("Enter username and password")
            return
        user = auth.authenticate(
            username=username.value.strip(),
            password=password.value,
            session_factory=ctx.session_factory,
        )
        if user is None:
            _show_message("Invalid credentials")
            return
        ctx.current_user = user
        ctx.guest_mode = False
        _ensure_seed(user.id)
        _show_message(f"Welcome back, {user.username}")
        page.go("/dashboard")

    def start_guest_mode(_):
        try:
            guest = auth.start_guest_session(ctx.session_factory)
        except Exception as exc:  # pragma: no cover - user facing guard
            _show_message(f"Guest mode unavailable ({exc})")
            return
        ctx.current_user = guest
        ctx.guest_mode = True
        _ensure_seed(guest.id or 0)
        _show_message("Guest mode enabled. Data clears when you exit.")
        page.go("/dashboard")

    def handle_create_user(_):
        if not new_username.value or not new_password.value:
            _show_message("Provide username and password")
            return
        if new_password.value != confirm_password.value:
            _show_message("Passwords do not match")
            return
        try:
            role = "admin" if first_admin.value else "user"
            user = auth.create_user(
                username=new_username.value.strip(),
                password=new_password.value,
                role=role,
                session_factory=ctx.session_factory,
            )
        except Exception as exc:  # pragma: no cover - user facing validation
            _show_message(str(exc))
            return
        ctx.current_user = user
        ctx.guest_mode = False
        _ensure_seed(user.id)
        _show_message(f"Account created for {user.username}")
        page.go("/dashboard")

    cards = [
        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Text("Login", size=20, weight=ft.FontWeight.BOLD),
                        username,
                        password,
                        ft.FilledButton("Sign in", icon=ft.Icons.LOGIN, on_click=handle_login),
                    ],
                    spacing=12,
                ),
            ),
            elevation=2,
        ),
        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Text(
                            "Create account" if users_exist else "Create first user",
                            size=20,
                            weight=ft.FontWeight.BOLD,
                        ),
                        new_username,
                        new_password,
                        confirm_password,
                        first_admin,
                        ft.FilledButton(
                            "Create and continue",
                            icon=ft.Icons.PERSON_ADD,
                            on_click=handle_create_user,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            elevation=2,
        ),
        ft.Card(
            content=ft.Container(
                padding=20,
                content=ft.Column(
                    [
                        ft.Text("Try as guest", size=20, weight=ft.FontWeight.BOLD),
                        ft.Text(
                            "Use PocketSage without an account. We'll clear anything you add when you close.",
                            color=ft.Colors.ON_SURFACE_VARIANT,
                        ),
                        ft.FilledButton(
                            "Continue as guest",
                            icon=ft.Icons.LOCK_OPEN,
                            on_click=start_guest_mode,
                        ),
                    ],
                    spacing=12,
                ),
            ),
            elevation=2,
        ),
    ]

    content = ft.Column(
        [
            ft.Text("PocketSage", size=28, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Offline-first finance + habits. Sign in or create an account.",
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Container(height=16),
            ft.Row(cards, spacing=16, wrap=True),
            ft.Container(height=12),
            ft.Text("", ref=status_text, color=ft.Colors.ON_SURFACE_VARIANT),
        ],
        horizontal_alignment=ft.CrossAxisAlignment.START,
        spacing=8,
    )

    return ft.View(
        route="/login",
        controls=[
            ft.Container(
                width=800,
                content=content,
                padding=32,
                alignment=ft.alignment.center,
            )
        ],
        padding=0,
    )

"""Settings view implementation."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from ...services.admin_tasks import run_export
from .. import controllers
from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_settings_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the settings/admin view."""

    def _notify(message: str):
        page.snack_bar = ft.SnackBar(content=ft.Text(message))
        page.snack_bar.open = True
        page.update()

    # Theme toggle
    def toggle_theme(e):
        """Toggle between light and dark theme."""
        if page.theme_mode == ft.ThemeMode.DARK:
            page.theme_mode = ft.ThemeMode.LIGHT
            ctx.theme_mode = ft.ThemeMode.LIGHT
            theme_switch.value = False
        else:
            page.theme_mode = ft.ThemeMode.DARK
            ctx.theme_mode = ft.ThemeMode.DARK
            theme_switch.value = True
        page.update()

    theme_switch = ft.Switch(
        label="Dark Mode",
        value=page.theme_mode == ft.ThemeMode.DARK,
        on_change=toggle_theme,
    )

    # Database info
    db_path = ctx.config.DATA_DIR / ctx.config.DB_FILENAME

    # Build settings sections
    appearance_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Appearance", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    theme_switch,
                ],
            ),
            padding=20,
        ),
        elevation=2,
    )

    def export_data(_):
        try:
            exports_dir = ctx.config.DATA_DIR
            path = run_export(
                Path(exports_dir),
                session_factory=ctx.session_factory,
                user_id=ctx.require_user_id(),
            )
            _notify(f"Export ready: {path}")
        except Exception as exc:
            _notify(f"Export failed: {exc}")

    database_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Database", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Row(
                        [
                            ft.Text("Database Path:", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(str(db_path), size=14, selectable=True),
                        ],
                        spacing=8,
                    ),
                    ft.Container(height=8),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Backup Database",
                                icon=ft.Icons.BACKUP,
                                on_click=lambda _: _notify("Backup not yet implemented"),
                            ),
                            ft.FilledButton(
                                "Export Data",
                                icon=ft.Icons.DOWNLOAD,
                                on_click=export_data,
                            ),
                        ],
                        spacing=8,
                    ),
                ],
            ),
            padding=20,
        ),
        elevation=2,
    )

    about_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("About", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Row(
                        [
                            ft.Icon(
                                ft.Icons.ACCOUNT_BALANCE_WALLET, size=48, color=ft.Colors.PRIMARY
                            ),
                            ft.Container(width=16),
                            ft.Column(
                                [
                                    ft.Text("PocketSage", size=20, weight=ft.FontWeight.BOLD),
                                    ft.Text(
                                        "Version 0.1.0", size=14, color=ft.Colors.ON_SURFACE_VARIANT
                                    ),
                                    ft.Text(
                                        "Offline-first finance and habit tracking",
                                        size=14,
                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            padding=20,
        ),
        elevation=2,
    )

    # Data section
    data_section = ft.Card(
        content=ft.Container(
            content=ft.Column(
                [
                    ft.Text("Data Management", size=18, weight=ft.FontWeight.BOLD),
                    ft.Container(height=16),
                    ft.Text(
                        "Manage your data and imports",
                        size=14,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(height=16),
                    ft.Row(
                        [
                            ft.FilledButton(
                                "Import Transactions",
                                icon=ft.Icons.UPLOAD_FILE,
                                on_click=lambda _: controllers.start_ledger_import(ctx, page),
                            ),
                            ft.FilledButton(
                                "Import Portfolio",
                                icon=ft.Icons.UPLOAD,
                                on_click=lambda _: controllers.start_portfolio_import(ctx, page),
                            ),
                            ft.TextButton(
                                "CSV Help",
                                icon=ft.Icons.HELP_OUTLINE,
                                on_click=lambda _: controllers.go_to_help(page),
                            ),
                        ],
                        spacing=8,
                    ),
                ],
            ),
            padding=20,
        ),
        elevation=2,
    )

    # Build content
    content = ft.Column(
        [
            ft.Text("Settings", size=24, weight=ft.FontWeight.BOLD),
            ft.Container(height=16),
            appearance_section,
            ft.Container(height=16),
            database_section,
            ft.Container(height=16),
            data_section,
            ft.Container(height=16),
            about_section,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Settings", page)
    main_layout = build_main_layout(ctx, page, "/settings", content)

    return ft.View(
        route="/settings",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

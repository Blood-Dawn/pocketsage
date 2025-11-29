from __future__ import annotations

import flet as ft

from ..components import build_app_bar, build_main_layout
from ..context import AppContext

# Snapshot of README content (keep in sync manually when README changes)
README_TEXT = """
# PocketSage

Offline-first personal finance and habit tracker with ledger, budgets, habits, debts, portfolio, and admin/backup tooling. Desktop-only (Flet), no external APIs, local SQLite/SQLModel with optional SQLCipher.

## Quickstart
- Python 3.11
- pip install -e ".[dev]"
- python run_desktop.py

## Features
- Ledger with CSV import/export
- Budgets and reports
- Habits tracking
- Debts and payoff projections
- Portfolio holdings and allocation
- Admin seed/export/reset

Data stored under instance/ by default. Configure via POCKETSAGE_ env vars.
"""


def build_about_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Simple About page that renders README.md content."""

    md = ft.Markdown(
        README_TEXT,
        selectable=True,
        extension_set=ft.MarkdownExtensionSet.GITHUB_WEB,
        code_theme="atom-one-dark",
        expand=True,
        on_tap_link=lambda e: page.launch_url(e.data) if hasattr(page, "launch_url") else None,
    )

    body = ft.Column(
        controls=[
            ft.Text("About PocketSage", size=24, weight=ft.FontWeight.BOLD),
            ft.Divider(),
            md,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    app_bar = build_app_bar(ctx, "About", page)
    layout = build_main_layout(ctx, page, "/about", body, use_menu_bar=True)

    return ft.View(route="/about", appbar=app_bar, controls=layout, padding=0)

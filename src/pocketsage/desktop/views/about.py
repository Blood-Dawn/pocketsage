from __future__ import annotations

import flet as ft

from ..components import build_app_bar, build_main_layout
from ..context import AppContext


def _bullet(text: str) -> ft.Row:
    """Render a simple bullet row with muted text."""
    return ft.Row(
        [
            ft.Text("-", weight=ft.FontWeight.BOLD),
            ft.Text(text, expand=True, color=ft.Colors.ON_SURFACE_VARIANT),
        ],
        spacing=8,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _shortcut(key: str, description: str) -> ft.Row:
    """Render a keyboard shortcut row."""
    return ft.Row(
        [
            ft.Container(
                content=ft.Text(key, weight=ft.FontWeight.BOLD),
                padding=ft.padding.symmetric(horizontal=8, vertical=4),
                border_radius=6,
                bgcolor=getattr(ft.Colors, "SURFACE_CONTAINER_LOW", ft.Colors.SURFACE),
            ),
            ft.Text(description, expand=True, color=ft.Colors.ON_SURFACE_VARIANT),
        ],
        spacing=10,
        vertical_alignment=ft.CrossAxisAlignment.START,
    )


def _card(title: str, lines: list[ft.Control]) -> ft.Card:
    """Wrap a set of controls in a card with a heading."""
    return ft.Card(
        content=ft.Container(
            padding=16,
            content=ft.Column(
                [ft.Text(title, size=18, weight=ft.FontWeight.BOLD), *lines],
                spacing=10,
            ),
        )
    )


def build_about_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Rich About page summarizing PocketSage usage and guardrails."""

    overview = ft.Column(
        [
            ft.Text("About PocketSage", size=24, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Offline-first personal finance and habit tracker for desktop. "
                "Data stays local in SQLite/SQLModel with an optional SQLCipher toggle; no external APIs or telemetry.",
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
        ],
        spacing=6,
    )

    release_notes = _card(
        "Release snapshot (v1.0.0)",
        [
            ft.Text(
                "PocketSage is an offline-first desktop app for tracking money, debts, habits, and a simple portfolio. "
                "Data stays local in SQLite under instance/ (override with POCKETSAGE_DATA_DIR); no cloud or telemetry. "
                "SQLCipher flags are scaffolded for future encrypted builds.",
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
            ft.Text(
                "Highlights: guest-first desktop shell (Flet) with nav rail, theme switcher, quick actions, and shortcuts "
                "(Ctrl+N new transaction, Ctrl+Shift+H new habit, Ctrl+1..7 nav); admin toolkit for demo seed/reset, backup/export/restore "
                "with secure dirs and 5 export retention; packaging via PyInstaller/Flet pack and Inno Setup (dist\\PocketSage.exe, dist\\installer\\PocketSage-Setup-1.0.0.exe); "
                "roadmap/docs with milestone planning and ops runbooks.",
                color=ft.Colors.ON_SURFACE_VARIANT,
                size=13,
            ),
            ft.Text(
                "Core features: ledger CRUD with validation, flash toasts, pagination/filters, rollups, CSV export; budgets with per-category lines and progress; "
                "habits CRUD/archive, optimistic toggles, streaks/heatmaps; debts with validation, payoff summaries/charts, payment schedule; "
                "portfolio CRUD with grouping/sorting/filtering and CSV preview; reports/dashboard with spending/budget/habits/debt/alloc charts and CSV/PNG/ZIP exports.",
                color=ft.Colors.ON_SURFACE_VARIANT,
                size=13,
            ),
            ft.Text(
                "Known limits: CSV import currently broken/hidden; delete buttons in grids not fully wired—use Admin → Delete Data; budget line errors need hardening; "
                "no cloud sync or multi-user; SQLCipher not finalized; no watcher/auto-import yet; limited UI automation/perf coverage; uninstall keeps user data (delete/reset via Admin).",
                color=ft.Colors.ON_SURFACE_VARIANT,
                size=13,
            ),
            ft.Text(
                "Getting started: install PocketSage-Setup-1.0.0.exe (defaults to C:\\Program Files\\PocketSage), launch, toggle Admin, run Demo Seed, switch back to Guest, "
                "exports/backups under instance/exports (override via POCKETSAGE_DATA_DIR). Full changelog: github.com/Blood-Dawn/pocketsage/commits/V1.",
                color=ft.Colors.ON_SURFACE_VARIANT,
                size=13,
            ),
        ],
    )

    key_areas = _card(
        "What you can do",
        [
            _bullet("Ledger: add/edit transactions, filter by date/category/memo, and import/export CSV with idempotent transaction_id handling."),
            _bullet("Budgets: build monthly budgets, copy last month, and track category progress with rollover toggles."),
            _bullet("Habits: create/archive habits, mark today's completion, and review streaks plus heatmaps for the last 28–180 days."),
            _bullet("Debts: manage liabilities, record payments, and compare snowball vs avalanche payoff with a timeline chart."),
            _bullet("Portfolio: track holdings per account, import/export CSVs, and view allocation charts."),
            _bullet("Reports/Admin: export spending and payoff bundles (CSV + PNG), run demo seed/reset, toggle themes, and manage backups."),
        ],
    )

    quick_start = _card(
        "Quick start",
        [
            ft.Text("1) Install (Python 3.11): pip install -e \".[dev]\"", color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text("2) Launch: python run_desktop.py", color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text('3) In Settings/Admin, click "Seed Demo Data" to explore sample ledger, habits, debts, and portfolio.', color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text("4) Add a transaction or import a CSV from Ledger; export bundles from Reports/Admin when ready.", color=ft.Colors.ON_SURFACE_VARIANT),
        ],
    )

    shortcuts = _card(
        "Keyboard shortcuts",
        [
            _shortcut("Ctrl+1..6", "Jump between Ledger, Habits, Debts, Portfolio, Reports, Settings."),
            _shortcut("Ctrl+N", "Navigate to Ledger for quick transaction entry."),
            _shortcut("Ctrl+Shift+H", "Jump to Habits to log today’s streak."),
        ],
    )

    data_privacy = _card(
        "Data, privacy, and storage",
        [
            _bullet("Data directory defaults to instance/; if that path is protected (e.g., Program Files) we fall back to %LOCALAPPDATA%/PocketSage. Override with POCKETSAGE_DATA_DIR. The folder is auto-created."),
            _bullet("Database: SQLite (pocketsage.db) via SQLModel. SQLCipher-ready using POCKETSAGE_USE_SQLCIPHER=true and POCKETSAGE_SQLCIPHER_KEY."),
            _bullet("Exports and backups: ZIPs land under instance/exports (keeps 5 latest) and instance/backups; session logs live in instance/logs/."),
            _bullet("Network: fully offline - no external API calls or telemetry."),
        ],
    )

    import_export = _card(
        "Import/export at a glance",
        [
            _bullet("Ledger CSV headers: date, amount, memo, category, account; optional currency and transaction_id for de-duplication."),
            _bullet("Portfolio CSV headers: account, symbol, shares, price, as_of (see scripts/csv_samples/portfolio.csv for a template)."),
            _bullet("Reports/export bundles include CSV + PNG artifacts and respect the five-export retention policy."),
        ],
    )

    troubleshooting = _card(
        "Tips and troubleshooting",
        [
            _bullet("Use the month selector/quick ranges to refresh budgets and reports if values look stale."),
            _bullet("If file pickers do not open, retry after ensuring the app can read/write to your data directory."),
            _bullet("Check <data-dir>/logs/session.log when something crashes; reset demo data from Settings/Admin to start fresh."),
            _bullet("Make targets and scripts live at the repo root: make dev, make test, make package."),
        ],
    )

    body = ft.Column(
        controls=[
            overview,
            ft.Divider(),
            release_notes,
            ft.Container(height=10),
            key_areas,
            ft.Container(height=10),
            quick_start,
            ft.Container(height=10),
            shortcuts,
            ft.Container(height=10),
            data_privacy,
            ft.Container(height=10),
            import_export,
            ft.Container(height=10),
            troubleshooting,
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    app_bar = build_app_bar(ctx, "About", page)
    layout = build_main_layout(ctx, page, "/about", body, use_menu_bar=True)

    return ft.View(route="/about", appbar=app_bar, controls=layout, padding=0)

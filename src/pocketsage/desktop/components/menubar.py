"""HomeBank-style top menu bar for desktop app.

Implements a clean top menu bar similar to HomeBank's UI with dropdown menus:
- File: New, Open, Save, Import, Export, Backup, Restore, Quit
- Edit: Categories, Accounts, Budgets (future: Preferences)
- View: (future: filters, sorting options)
- Manage: Transactions, Habits, Debts, Portfolio
- Reports: Dashboard, Monthly, Year-to-Date, Charts
- Tools: Demo Seed, Reset Data (admin only)
- Help: CSV Help, About
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

if TYPE_CHECKING:
    from ..context import AppContext

from .. import controllers


def build_menu_bar(ctx: AppContext, page: ft.Page) -> ft.MenuBar:
    """Build HomeBank-style menu bar with dropdowns.

    Returns a MenuBar control that should be placed at the top of the view.
    """

    is_admin = ctx.current_user and ctx.current_user.role == "admin"

    # File menu
    file_menu = ft.SubmenuButton(
        content=ft.Text("File"),
        controls=[
            ft.MenuItemButton(
                content=ft.Text("New Transaction  Ctrl+N"),
                leading=ft.Icon(ft.Icons.ADD),
                on_click=lambda _: page.go("/add-data"),
            ),
            ft.MenuItemButton(
                content=ft.Text("Add Data"),
                leading=ft.Icon(ft.Icons.ADD_BOX),
                on_click=lambda _: page.go("/add-data"),
            ),
            ft.MenuItemButton(
                content=ft.Text("Import CSV  Ctrl+I"),
                leading=ft.Icon(ft.Icons.UPLOAD_FILE),
                on_click=lambda _: controllers.start_ledger_import(ctx, page),
            ),
            ft.MenuItemButton(
                content=ft.Text("Export CSV"),
                leading=ft.Icon(ft.Icons.DOWNLOAD),
                on_click=lambda _: _export_ledger(ctx, page),
            ),
            ft.Divider(),
            ft.MenuItemButton(
                content=ft.Text("Backup"),
                leading=ft.Icon(ft.Icons.BACKUP),
                on_click=lambda _: _backup_database(ctx, page),
            ),
            ft.MenuItemButton(
                content=ft.Text("Restore"),
                leading=ft.Icon(ft.Icons.RESTORE),
                on_click=lambda _: _restore_database(ctx, page),
            ),
            ft.Divider(),
            ft.MenuItemButton(
                content=ft.Text("Quit  Ctrl+Q"),
                leading=ft.Icon(ft.Icons.EXIT_TO_APP),
                on_click=lambda _: page.window.destroy(),
            ),
        ],
    )

    # Edit menu
    edit_menu = ft.SubmenuButton(
        content=ft.Text("Edit"),
        controls=[
            ft.MenuItemButton(
                content=ft.Text("Categories"),
                leading=ft.Icon(ft.Icons.CATEGORY),
                on_click=lambda _: _open_categories_dialog(ctx, page),
            ),
            ft.MenuItemButton(
                content=ft.Text("Accounts"),
                leading=ft.Icon(ft.Icons.ACCOUNT_BALANCE),
                on_click=lambda _: _open_accounts_dialog(ctx, page),
            ),
            ft.MenuItemButton(
                content=ft.Text("Budgets"),
                leading=ft.Icon(ft.Icons.SAVINGS),
                on_click=lambda _: page.go("/budgets"),
            ),
        ],
    )

    # View menu (placeholder for future features)
    view_menu = ft.SubmenuButton(
        content=ft.Text("View"),
        controls=[
            ft.MenuItemButton(
                content=ft.Text("Dashboard"),
                leading=ft.Icon(ft.Icons.DASHBOARD),
                on_click=lambda _: page.go("/dashboard"),
            ),
            ft.MenuItemButton(
                content=ft.Text("Ledger"),
                leading=ft.Icon(ft.Icons.RECEIPT_LONG),
                on_click=lambda _: page.go("/ledger"),
            ),
        ],
    )

    # Manage menu
    manage_menu = ft.SubmenuButton(
        content=ft.Text("Manage"),
        controls=[
            ft.MenuItemButton(
                content=ft.Text("Transactions  Ctrl+1"),
                leading=ft.Icon(ft.Icons.RECEIPT_LONG),
                on_click=lambda _: controllers.navigate(page, "/ledger"),
            ),
            ft.MenuItemButton(
                content=ft.Text("Habits  Ctrl+2"),
                leading=ft.Icon(ft.Icons.CHECK_CIRCLE),
                on_click=lambda _: controllers.navigate(page, "/habits"),
            ),
            ft.MenuItemButton(
                content=ft.Text("Debts  Ctrl+3"),
                leading=ft.Icon(ft.Icons.CREDIT_CARD),
                on_click=lambda _: controllers.navigate(page, "/debts"),
            ),
            ft.MenuItemButton(
                content=ft.Text("Portfolio  Ctrl+4"),
                leading=ft.Icon(ft.Icons.SHOW_CHART),
                on_click=lambda _: controllers.navigate(page, "/portfolio"),
            ),
            ft.MenuItemButton(
                content=ft.Text("Budgets  Ctrl+5"),
                leading=ft.Icon(ft.Icons.SAVINGS),
                on_click=lambda _: controllers.navigate(page, "/budgets"),
            ),
        ],
    )

    # Reports menu
    reports_menu = ft.SubmenuButton(
        content=ft.Text("Reports"),
        controls=[
            ft.MenuItemButton(
                content=ft.Text("Dashboard"),
                leading=ft.Icon(ft.Icons.DASHBOARD),
                on_click=lambda _: controllers.navigate(page, "/dashboard"),
            ),
            ft.MenuItemButton(
                content=ft.Text("All Reports  Ctrl+6"),
                leading=ft.Icon(ft.Icons.ASSESSMENT),
                on_click=lambda _: controllers.navigate(page, "/reports"),
            ),
        ],
    )

    # Tools menu (admin features)
    tools_controls = []
    if is_admin:
        tools_controls.extend([
            ft.MenuItemButton(
                content=ft.Text("Run Demo Seed"),
                leading=ft.Icon(ft.Icons.PLAY_ARROW),
                on_click=lambda _: _run_demo_seed(ctx, page),
            ),
            ft.MenuItemButton(
                content=ft.Text("Reset Demo Data"),
                leading=ft.Icon(ft.Icons.REFRESH),
                on_click=lambda _: _reset_demo_data(ctx, page),
            ),
            ft.Divider(),
        ])

    tools_controls.append(
        ft.MenuItemButton(
            content=ft.Text("Settings  Ctrl+,"),
            leading=ft.Icon(ft.Icons.SETTINGS),
            on_click=lambda _: controllers.navigate(page, "/settings"),
        )
    )

    tools_menu = ft.SubmenuButton(
        content=ft.Text("Tools"),
        controls=tools_controls,
    )

    # Help menu
    help_menu = ft.SubmenuButton(
        content=ft.Text("Help"),
        controls=[
            ft.MenuItemButton(
                content=ft.Text("CSV Import Help"),
                leading=ft.Icon(ft.Icons.HELP),
                on_click=lambda _: controllers.go_to_help(page),
            ),
            ft.MenuItemButton(
                content=ft.Text("About PocketSage"),
                leading=ft.Icon(ft.Icons.INFO),
                on_click=lambda _: _show_about_dialog(page),
            ),
        ],
    )

    # Build the menu bar
    return ft.MenuBar(
        controls=[
            file_menu,
            edit_menu,
            view_menu,
            manage_menu,
            reports_menu,
            tools_menu,
            help_menu,
        ],
    )


# Helper functions for menu actions

def _open_transaction_dialog(ctx: AppContext, page: ft.Page):
    """Open new transaction dialog (delegates to ledger view helper)."""
    from .dialogs import show_transaction_dialog

    def _refresh_current_view():
        """Refresh the current view after adding transaction."""
        # Trigger a page update or navigation refresh
        page.update()

    show_transaction_dialog(ctx, page, on_save_callback=_refresh_current_view)


def _open_categories_dialog(ctx: AppContext, page: ft.Page):
    """Open category management dialog (FR-9)."""
    from .dialogs import show_category_list_dialog
    show_category_list_dialog(ctx, page)


def _open_accounts_dialog(ctx: AppContext, page: ft.Page):
    """Open account management dialog."""
    from .dialogs import show_account_list_dialog

    show_account_list_dialog(ctx, page)


def _export_ledger(ctx: AppContext, page: ft.Page):
    """Export ledger to CSV."""
    # Delegate to ledger export
    controllers.navigate(page, "/ledger")
    page.snack_bar = ft.SnackBar(
        content=ft.Text("Go to Ledger page and click Export CSV button")
    )
    page.snack_bar.open = True
    page.update()


def _backup_database(ctx: AppContext, page: ft.Page):
    """Backup database."""
    controllers.navigate(page, "/settings")
    page.snack_bar = ft.SnackBar(
        content=ft.Text("Use Settings page to backup database")
    )
    page.snack_bar.open = True
    page.update()


def _restore_database(ctx: AppContext, page: ft.Page):
    """Restore database from backup."""
    controllers.navigate(page, "/settings")
    page.snack_bar = ft.SnackBar(
        content=ft.Text("Use Settings page to restore from backup")
    )
    page.snack_bar.open = True
    page.update()


def _run_demo_seed(ctx: AppContext, page: ft.Page):
    """Run demo seed (admin only)."""
    controllers.navigate(page, "/admin")
    page.snack_bar = ft.SnackBar(
        content=ft.Text("Use Admin page to run demo seed")
    )
    page.snack_bar.open = True
    page.update()


def _reset_demo_data(ctx: AppContext, page: ft.Page):
    """Reset demo data (admin only)."""
    controllers.navigate(page, "/admin")
    page.snack_bar = ft.SnackBar(
        content=ft.Text("Use Admin page to reset demo data")
    )
    page.snack_bar.open = True
    page.update()


def _show_about_dialog(page: ft.Page):
    """Show about dialog with app info."""
    dialog = ft.AlertDialog(
        title=ft.Text("About PocketSage"),
        content=ft.Column(
            controls=[
                ft.Text("PocketSage", size=18, weight=ft.FontWeight.BOLD),
                ft.Text("Offline Personal Finance & Habits Tracker"),
                ft.Divider(),
                ft.Text("Version: 1.0.0-beta"),
                ft.Text("Built with: Python 3.11, Flet, SQLModel"),
                ft.Divider(),
                ft.Text("Privacy-first, desktop-only, no external APIs."),
                ft.Text("All data stored locally under instance/ directory."),
            ],
            tight=True,
            spacing=8,
        ),
        actions=[
            ft.TextButton("Close", on_click=lambda _: _close_dialog(page, dialog))
        ],
    )
    page.dialog = dialog
    dialog.open = True
    page.update()


def _close_dialog(page: ft.Page, dialog: ft.AlertDialog):
    """Close a dialog."""
    dialog.open = False
    page.update()

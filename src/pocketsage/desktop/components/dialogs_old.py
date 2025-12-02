"""Dialog components for the desktop app."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft


def show_error_dialog(page: ft.Page, title: str, message: str) -> None:
    """Show an error dialog."""

    def close_dialog(e):
        dialog.open = False
        try:
            page.update()
        except AssertionError:
            pass

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            ft.TextButton("OK", on_click=close_dialog),
        ],
    )

    page.dialog = dialog
    dialog.open = True
    try:
        page.update()
    except AssertionError:
        pass


def show_confirm_dialog(
    page: ft.Page,
    title: str,
    message: str,
    on_confirm: Callable,
    on_cancel: Optional[Callable] = None,
) -> None:
    """Show a confirmation dialog."""

    def handle_confirm(e):
        dialog.open = False
        page.update()
        if on_confirm:
            on_confirm()

    def handle_cancel(e):
        dialog.open = False
        try:
            page.update()
        except AssertionError:
            pass
        if on_cancel:
            on_cancel()

    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text(title),
        content=ft.Text(message),
        actions=[
            ft.TextButton("Cancel", on_click=handle_cancel),
            ft.FilledButton("Confirm", on_click=handle_confirm),
        ],
    )

    page.dialog = dialog
    dialog.open = True
    try:
        page.update()
    except AssertionError:
        pass


def safe_open_dialog(page: ft.Page, dialog: ft.AlertDialog) -> None:
    """Open a dialog and best-effort refresh without raising when detached."""
    page.dialog = dialog
    dialog.open = True
    try:
        page.update()
    except AssertionError:
        # Headless/preview contexts may not attach the dialog to a live page
        pass

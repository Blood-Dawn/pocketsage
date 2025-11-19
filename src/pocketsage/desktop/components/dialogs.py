"""Dialog components for the desktop app."""

from __future__ import annotations

from typing import Callable, Optional

import flet as ft


def show_error_dialog(page: ft.Page, title: str, message: str) -> None:
    """Show an error dialog."""

    def close_dialog(e):
        dialog.open = False
        page.update()

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
    page.update()


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
        page.update()
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
    page.update()

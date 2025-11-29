"""Reusable widget components for the desktop app."""

from __future__ import annotations

from typing import Optional

import flet as ft


def build_card(
    title: str,
    content: ft.Control,
    actions: Optional[list[ft.Control]] = None,
) -> ft.Card:
    """Build a standard card with title and content."""

    header = ft.Container(
        content=ft.Row(
            [
                ft.Text(title, size=18, weight=ft.FontWeight.BOLD),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        ),
        padding=ft.padding.only(left=16, right=16, top=16, bottom=8),
    )

    card_content = ft.Column(
        [
            header,
            ft.Divider(height=1),
            ft.Container(
                content=content,
                padding=16,
            ),
        ],
        spacing=0,
    )

    if actions:
        card_content.controls.append(
            ft.Container(
                content=ft.Row(actions, alignment=ft.MainAxisAlignment.END),
                padding=ft.padding.only(left=16, right=16, bottom=16),
            )
        )

    return ft.Card(
        content=card_content,
        elevation=2,
    )


def build_stat_card(
    label: str,
    value: str,
    icon: Optional[str] = None,
    color: Optional[str] = None,
    subtitle: Optional[str] = None,
) -> ft.Card:
    """Build a statistic card."""

    icon_widget = None
    if icon:
        icon_widget = ft.Icon(
            icon,
            size=40,
            color=color or ft.Colors.PRIMARY,
        )

    value_text = ft.Text(
        value,
        size=32,
        weight=ft.FontWeight.BOLD,
        color=color,
    )

    label_text = ft.Text(
        label,
        size=14,
        color=ft.Colors.ON_SURFACE_VARIANT,
    )

    content_column = ft.Column(
        [value_text, label_text],
        spacing=4,
        horizontal_alignment=ft.CrossAxisAlignment.START,
    )

    if subtitle:
        content_column.controls.append(
            ft.Text(subtitle, size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        )

    if icon_widget:
        card_content = ft.Row(
            [
                icon_widget,
                ft.Container(width=16),
                content_column,
            ],
            alignment=ft.MainAxisAlignment.START,
        )
    else:
        card_content = content_column

    return ft.Card(
        content=ft.Container(
            content=card_content,
            padding=20,
        ),
        elevation=2,
    )


def build_progress_bar(
    current: float,
    maximum: float,
    label: Optional[str] = None,
    color: Optional[str] = None,
) -> ft.Column:
    """Build a labeled progress bar."""

    if maximum > 0:
        percentage = min((current / maximum) * 100, 100)
        progress_value = current / maximum
    else:
        percentage = 0
        progress_value = 0

    bar_color = color
    if bar_color is None:
        if percentage > 100:
            bar_color = ft.Colors.ERROR
        elif percentage > 90:
            bar_color = ft.Colors.AMBER
        else:
            bar_color = ft.Colors.PRIMARY

    label_row = ft.Row(
        [
            ft.Text(label or "", size=14),
            ft.Text(
                f"${current:,.2f} / ${maximum:,.2f}",
                size=14,
                color=ft.Colors.ON_SURFACE_VARIANT,
            ),
        ],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    progress_bar = ft.ProgressBar(
        value=min(progress_value, 1.0),
        color=bar_color,
        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        height=8,
    )

    percentage_text = ft.Text(
        f"{percentage:.1f}%",
        size=12,
        color=bar_color,
    )

    return ft.Column(
        [
            label_row,
            progress_bar,
            percentage_text,
        ],
        spacing=4,
    )


def empty_state(message: str) -> ft.Container:
    """Simple empty-state placeholder."""

    return ft.Container(
        content=ft.Column(
            [
                ft.Icon(ft.Icons.INBOX, size=40, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(message, color=ft.Colors.ON_SURFACE_VARIANT),
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
        ),
        padding=20,
    )

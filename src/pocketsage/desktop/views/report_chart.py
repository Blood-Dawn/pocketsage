"""Dedicated view for expanded report charts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import flet as ft

from .. import controllers
from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_report_chart_view(ctx: "AppContext", page: ft.Page) -> ft.View:
    """Render a single chart in a full-screen friendly view."""

    payload = getattr(ctx, "pending_chart", None) or {}
    title = payload.get("title") or "Report chart"
    image_path = payload.get("image_path")
    extra_content = payload.get("content")
    drill_route = payload.get("drill_route")
    ctx.pending_chart = None

    chart_control: ft.Control
    if image_path:
        path = Path(image_path)
        if path.exists():
            chart_control = ft.Image(
                src=str(path),
                fit=ft.ImageFit.CONTAIN,
                width=1100,
                height=750,
            )
        else:
            chart_control = ft.Column(
                controls=[
                    ft.Icon(ft.Icons.IMAGE_NOT_SUPPORTED, size=48, color=ft.Colors.OUTLINE),
                    ft.Text(f"Chart not available at {path}", color=ft.Colors.ON_SURFACE_VARIANT),
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                spacing=8,
            )
    elif extra_content:
        chart_control = ft.Container(content=extra_content, padding=12)
    else:
        chart_control = ft.Text("No chart available", color=ft.Colors.ON_SURFACE_VARIANT)

    def _back(_=None):
        controllers.navigate(page, "/reports")

    def _drill(_=None):
        if drill_route:
            controllers.navigate(page, drill_route)

    actions: list[ft.Control] = [
        ft.FilledButton("Back to reports", icon=ft.Icons.ARROW_BACK, on_click=_back),
    ]
    if drill_route:
        actions.append(
            ft.TextButton("Go to details", icon=ft.Icons.OPEN_IN_NEW, on_click=_drill)
        )

    body = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.Text(title, size=24, weight=ft.FontWeight.BOLD),
                    ft.Row(actions, spacing=8),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                wrap=True,
            ),
            ft.Container(height=12),
            ft.Container(
                chart_control,
                border_radius=8,
                border=ft.border.all(1, ft.Colors.OUTLINE_VARIANT),
                padding=12,
                expand=True,
                alignment=ft.alignment.center,
            ),
        ],
        spacing=12,
        expand=True,
        scroll=ft.ScrollMode.AUTO,
    )

    return ft.View(
        route="/reports/chart",
        appbar=build_app_bar(ctx, "Report chart", page),
        controls=build_main_layout(ctx, page, "/reports/chart", body, use_menu_bar=True),
        padding=0,
    )

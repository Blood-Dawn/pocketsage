"""Habits view implementation."""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

import flet as ft

from ...models.habit import HabitEntry
from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_habits_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the habits view."""

    habit_list_ref = ft.Ref[ft.Column]()
    heatmap_ref = ft.Ref[ft.GridView]()
    selected_ref = ft.Ref[ft.Text]()
    streak_ref = ft.Ref[ft.Text]()
    longest_ref = ft.Ref[ft.Text]()
    selected_habit: int | None = None

    def render_heatmap(habit_id: int):
        today = date.today()
        start = today - timedelta(days=27)
        entries = ctx.habit_repo.get_entries_for_habit(habit_id, start, today)
        completed = {e.occurred_on for e in entries if e.value > 0}
        cells: list[ft.Control] = []
        day = start
        while day <= today:
            is_done = day in completed
            color = ft.colors.GREEN if is_done else ft.colors.SURFACE_VARIANT
            cells.append(
                ft.Container(
                    width=20,
                    height=20,
                    bgcolor=color,
                    border_radius=4,
                    tooltip=day.isoformat(),
                )
            )
            day += timedelta(days=1)
        heatmap_ref.current.controls = cells
        heatmap_ref.current.update()

    def select_habit(hid: int, name: str):
        nonlocal selected_habit
        selected_habit = hid
        selected_ref.current.value = name
        streak_ref.current.value = f"Current streak: {ctx.habit_repo.get_current_streak(hid)}"
        longest_ref.current.value = f"Longest streak: {ctx.habit_repo.get_longest_streak(hid)}"
        render_heatmap(hid)
        page.update()

    def refresh_habit_list():
        habits = ctx.habit_repo.list_active()
        rows: list[ft.Control] = []
        today = date.today()

        for habit in habits:
            current_streak = ctx.habit_repo.get_current_streak(habit.id)
            longest_streak = ctx.habit_repo.get_longest_streak(habit.id)
            today_entry = ctx.habit_repo.get_entry(habit.id, today)
            is_completed = today_entry is not None and today_entry.value > 0

            def toggle_habit(_e, habit_id=habit.id):
                entry = ctx.habit_repo.get_entry(habit_id, today)
                if entry:
                    ctx.habit_repo.delete_entry(habit_id, today)
                else:
                    ctx.habit_repo.upsert_entry(HabitEntry(habit_id=habit_id, occurred_on=today, value=1))
                refresh_habit_list()
                page.snack_bar = ft.SnackBar(content=ft.Text("Habit updated"))
                page.snack_bar.open = True
                page.update()

            rows.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Switch(value=is_completed, on_change=toggle_habit),
                                ft.Column(
                                    [
                                        ft.Text(habit.name, size=16, weight=ft.FontWeight.BOLD),
                                        ft.Text(habit.description or "No description", size=12, color=ft.colors.ON_SURFACE_VARIANT),
                                        ft.Text(f"Current: {current_streak} • Longest: {longest_streak}", size=12, color=ft.colors.ON_SURFACE_VARIANT),
                                    ],
                                    expand=True,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=12,
                        on_click=lambda _e, hid=habit.id, name=habit.name: select_habit(hid, name),
                    )
                )
            )

        if not rows:
            rows.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, size=64, color=ft.colors.ON_SURFACE_VARIANT),
                            ft.Text("No active habits", size=20, weight=ft.FontWeight.BOLD),
                            ft.Text("Create your first habit to start tracking", color=ft.colors.ON_SURFACE_VARIANT),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=24,
                )
            )

        habit_list_ref.current.controls = rows
        page.update()

    habit_list = ft.Column(ref=habit_list_ref, spacing=8, expand=True)
    habit_list_ref.current = habit_list

    heatmap = ft.GridView(
        ref=heatmap_ref,
        runs_count=7,
        max_extent=24,
        child_aspect_ratio=1.0,
        spacing=4,
        run_spacing=4,
        expand=True,
    )

    detail_panel = ft.Column(
        [
            ft.Text("Habit detail", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("", ref=selected_ref, size=20, weight=ft.FontWeight.BOLD),
            ft.Text("", ref=streak_ref),
            ft.Text("", ref=longest_ref),
            ft.Text("Last 28 days", weight=ft.FontWeight.BOLD),
            heatmap,
        ],
        spacing=8,
        expand=True,
    )

    refresh_habit_list()
    active = ctx.habit_repo.list_active()
    if active:
        select_habit(active[0].id, active[0].name)

    content = ft.Row(
        [
            ft.Column(
                [
                    ft.Row(
                        [
                            ft.Text("Habits", size=24, weight=ft.FontWeight.BOLD),
                            ft.Text(date.today().strftime("%A, %B %d, %Y"), color=ft.colors.ON_SURFACE_VARIANT),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=8),
                    habit_list,
                ],
                expand=True,
            ),
            ft.VerticalDivider(width=1),
            ft.Container(content=detail_panel, width=320, padding=12),
        ],
        expand=True,
    )

    app_bar = build_app_bar(ctx, "Habits", page)
    main_layout = build_main_layout(ctx, page, "/habits", content)

    return ft.View(
        route="/habits",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

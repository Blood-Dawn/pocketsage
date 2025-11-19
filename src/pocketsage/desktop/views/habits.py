"""Habits view implementation."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING

import flet as ft

from ...models.habit import HabitEntry
from ..components import build_app_bar, build_main_layout

if TYPE_CHECKING:
    from ..context import AppContext


def build_habits_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the habits view."""

    habit_list_ref = ft.Ref[ft.Column]()

    def refresh_habit_list():
        """Refresh the habit list."""
        habits = ctx.habit_repo.list_active()
        rows = []

        today = date.today()

        for habit in habits:
            # Get current streak
            current_streak = ctx.habit_repo.get_current_streak(habit.id)

            # Get longest streak
            longest_streak = ctx.habit_repo.get_longest_streak(habit.id)

            # Check if completed today
            today_entry = ctx.habit_repo.get_entry(habit.id, today)
            is_completed = today_entry is not None and today_entry.value > 0

            def toggle_habit(e, habit_id=habit.id, completed=is_completed):
                """Toggle habit completion for today."""
                if completed:
                    # Remove entry
                    ctx.habit_repo.delete_entry(habit_id, today)
                else:
                    # Add entry
                    entry = HabitEntry(habit_id=habit_id, occurred_on=today, value=1)
                    ctx.habit_repo.upsert_entry(entry)

                refresh_habit_list()

            rows.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            [
                                ft.Checkbox(
                                    value=is_completed,
                                    on_change=toggle_habit,
                                ),
                                ft.Column(
                                    [
                                        ft.Text(
                                            habit.name,
                                            size=16,
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Text(
                                            habit.description or "No description",
                                            size=14,
                                            color=ft.colors.ON_SURFACE_VARIANT,
                                        ),
                                    ],
                                    expand=True,
                                ),
                                ft.Column(
                                    [
                                        ft.Row(
                                            [
                                                ft.Icon(ft.icons.LOCAL_FIRE_DEPARTMENT, size=20, color=ft.colors.ORANGE),
                                                ft.Text(
                                                    f"{current_streak} days",
                                                    size=14,
                                                ),
                                            ],
                                            spacing=4,
                                        ),
                                        ft.Text(
                                            f"Best: {longest_streak} days",
                                            size=12,
                                            color=ft.colors.ON_SURFACE_VARIANT,
                                        ),
                                    ],
                                    horizontal_alignment=ft.CrossAxisAlignment.END,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=16,
                    ),
                    elevation=1,
                )
            )

        if not rows:
            rows.append(
                ft.Container(
                    content=ft.Column(
                        [
                            ft.Icon(ft.icons.CHECK_CIRCLE_OUTLINE, size=64, color=ft.colors.ON_SURFACE_VARIANT),
                            ft.Container(height=16),
                            ft.Text(
                                "No active habits",
                                size=20,
                                weight=ft.FontWeight.BOLD,
                            ),
                            ft.Container(height=8),
                            ft.Text(
                                "Create your first habit to start tracking",
                                size=14,
                                color=ft.colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=40,
                )
            )

        habit_list_ref.current.controls = rows
        page.update()

    # Habit list
    habit_list = ft.Column(ref=habit_list_ref, spacing=16)

    # Initialize list
    refresh_habit_list()

    # Build content
    content = ft.Column(
        [
            ft.Row(
                [
                    ft.Text("Habits", size=24, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        date.today().strftime("%A, %B %d, %Y"),
                        size=14,
                        color=ft.colors.ON_SURFACE_VARIANT,
                    ),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
            ft.Container(height=16),
            habit_list,
        ],
        spacing=0,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    # Build main layout
    app_bar = build_app_bar(ctx, "Habits")
    main_layout = build_main_layout(page, "/habits", content)

    return ft.View(
        route="/habits",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

"""Dedicated habit edit page."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import flet as ft

from ...devtools import dev_log
from ...logging_config import get_logger
from ...models.habit import Habit, HabitEntry
from .. import controllers
from ..components import build_app_bar, build_main_layout, show_confirm_dialog, show_error_dialog
from ..constants import HABIT_CADENCE_OPTIONS

if TYPE_CHECKING:
    from ..context import AppContext

logger = get_logger(__name__)


def build_edit_habit_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build a dedicated edit page for habits."""

    uid = ctx.require_user_id()
    target = getattr(ctx, "pending_edit", None) or {}
    record_id = target.get("id")
    return_route = target.get("return_route") or "/habits"

    def _clear():
        ctx.pending_edit = None

    def _finish(message: str | None = None):
        if message:
            page.snack_bar = ft.SnackBar(content=ft.Text(message), show_close_icon=True)
            page.snack_bar.open = True
        ctx.pending_refresh_route = return_route
        _clear()
        controllers.navigate(page, return_route)

    def _back(_=None):
        _finish(None)

    habit = ctx.habit_repo.get_by_id(int(record_id or 0), user_id=uid) if record_id else None

    if not habit:
        fallback = ft.Column(
            [
                ft.Text("Select a habit to edit from the Habits page.", size=18, weight=ft.FontWeight.BOLD),
                ft.FilledButton("Back", icon=ft.Icons.ARROW_BACK, on_click=_back),
            ],
            spacing=12,
        )
        return ft.View(
            route="/edit-habit",
            appbar=build_app_bar(ctx, "Edit habit", page),
            controls=build_main_layout(
                ctx,
                page,
                "/edit-habit",
                ft.Column([fallback], expand=True, alignment=ft.MainAxisAlignment.CENTER),
                use_menu_bar=True,
            ),
            padding=0,
        )

    name_field = ft.TextField(label="Name", value=habit.name, width=260)
    desc_field = ft.TextField(label="Description", value=habit.description or "", width=320, multiline=True)
    cadence_dd = ft.Dropdown(
        label="Cadence",
        options=[ft.dropdown.Option(key, label) for key, label in HABIT_CADENCE_OPTIONS],
        value=habit.cadence,
        width=200,
    )
    reminder_field = ft.TextField(
        label="Reminder (HH:MM)",
        value=habit.reminder_time or "",
        width=160,
        hint_text="08:00",
    )
    active_switch = ft.Switch(label="Active", value=habit.is_active)

    window_days = 28
    today = date.today()
    start = today - timedelta(days=window_days - 1)
    existing_entries = {
        entry.occurred_on
        for entry in ctx.habit_repo.get_entries_for_habit(habit.id, start, today, user_id=uid)
        if entry.value > 0
    }
    day_lookup: dict[date, ft.Checkbox] = {}
    checkboxes: list[ft.Checkbox] = []
    for offset in range(window_days):
        day = start + timedelta(days=offset)
        cb = ft.Checkbox(label=day.strftime("%b %d"), value=day in existing_entries, width=110)
        day_lookup[day] = cb
        checkboxes.append(cb)

    def _validate_reminder(raw: str | None) -> str | None:
        if not raw:
            return None
        try:
            datetime.strptime(raw.strip(), "%H:%M")
            return raw.strip()
        except ValueError:
            return None

    def _save(_):
        try:
            if not (name_field.value or "").strip():
                raise ValueError("Name is required")
            reminder_value = _validate_reminder(reminder_field.value)
            if reminder_field.value and not reminder_value:
                raise ValueError("Reminder must use HH:MM")

            habit.name = name_field.value.strip()
            habit.description = desc_field.value or ""
            habit.cadence = cadence_dd.value or habit.cadence
            habit.reminder_time = reminder_value
            habit.is_active = bool(active_switch.value)
            ctx.habit_repo.update(habit, user_id=uid)

            selected_days = {day for day, cb in day_lookup.items() if cb.value}
            to_add = selected_days - existing_entries
            to_remove = existing_entries - selected_days
            for day in to_add:
                ctx.habit_repo.upsert_entry(
                    HabitEntry(habit_id=habit.id, occurred_on=day, value=1, user_id=uid),
                    user_id=uid,
                )
            for day in to_remove:
                ctx.habit_repo.delete_entry(habit.id, day, user_id=uid)

            current_streak = ctx.habit_repo.get_current_streak(habit.id, user_id=uid)
            longest_streak = ctx.habit_repo.get_longest_streak(habit.id, user_id=uid)
            dev_log(
                ctx.config,
                "Habit edited (page)",
                context={
                    "id": habit.id,
                    "current_streak": current_streak,
                    "longest_streak": longest_streak,
                },
            )
            _finish("Habit updated")
        except Exception as exc:
            dev_log(ctx.config, "Habit edit failed", exc=exc)
            show_error_dialog(page, "Save failed", str(exc))

    def _delete():
        try:
            all_entries = ctx.habit_repo.get_entries_for_habit(
                habit.id, date.min, date.max, user_id=uid  # type: ignore[arg-type]
            )
            for entry in all_entries:
                ctx.habit_repo.delete_entry(habit.id, entry.occurred_on, user_id=uid)
            ctx.habit_repo.delete(habit.id, user_id=uid)
            dev_log(ctx.config, "Habit deleted", context={"id": habit.id})
            _finish("Habit deleted")
        except Exception as exc:
            dev_log(ctx.config, "Habit delete failed", exc=exc)
            show_error_dialog(page, "Delete failed", str(exc))

    content = ft.Column(
        controls=[
            ft.Row(
                controls=[
                    ft.IconButton(icon=ft.Icons.ARROW_BACK, on_click=_back, tooltip="Back"),
                    ft.Text("Edit habit", size=26, weight=ft.FontWeight.BOLD),
                ],
                spacing=8,
            ),
            ft.Card(
                content=ft.Container(
                    padding=16,
                    content=ft.Column(
                        controls=[
                            ft.Row([name_field, cadence_dd, active_switch], spacing=12, wrap=True, run_spacing=8),
                            ft.Row([desc_field, reminder_field], spacing=12, wrap=True, run_spacing=8),
                            ft.Text("Recent completion history", weight=ft.FontWeight.BOLD),
                            ft.Row(controls=checkboxes, wrap=True, spacing=8, run_spacing=8),
                            ft.Row(
                                [
                                    ft.FilledButton("Save changes", icon=ft.Icons.SAVE, on_click=_save),
                                    ft.TextButton(
                                        "Delete",
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        style=ft.ButtonStyle(color=ft.Colors.RED),
                                        on_click=lambda _: show_confirm_dialog(
                                            page,
                                            "Delete habit",
                                            "This will remove the habit and its recent entries.",
                                            _delete,
                                        ),
                                    ),
                                    ft.TextButton("Cancel", icon=ft.Icons.CLOSE, on_click=_back),
                                ],
                                spacing=12,
                            ),
                        ],
                        spacing=12,
                    ),
                ),
                elevation=2,
            ),
        ],
        spacing=16,
        scroll=ft.ScrollMode.AUTO,
        expand=True,
    )

    return ft.View(
        route="/edit-habit",
        appbar=build_app_bar(ctx, "Edit habit", page),
        controls=build_main_layout(ctx, page, "/edit-habit", content, use_menu_bar=True),
        padding=0,
    )

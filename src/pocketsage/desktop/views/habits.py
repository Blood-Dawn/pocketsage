"""Habits view implementation."""
# TODO(@pocketsage-habits): Enhance visualizations (heatmaps, weekly summaries) and tie into Reports.

# TODO(@codex): Habits MVP features to implement/enhance:
#    - Habit CRUD (create/edit/archive habits) (DONE - basic create/archive)
#    - Daily toggle for marking habits complete (DONE)
#    - Streak calculation (current and longest) (DONE)
#    - Visualization (heatmap/calendar of completion) (DONE)
#    - Habit linking to spending notes (future stretch goal)
#    - Optional reminders (field exists, notification scheduling is future)

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING

import flet as ft

from .. import controllers
from ...devtools import dev_log
from ...models.habit import Habit, HabitEntry
from ...services.habits import reminder_placeholder
from ..components import build_app_bar, build_main_layout
from ..components.dialogs import show_habit_dialog
from ..constants import HABIT_CADENCE_OPTIONS

if TYPE_CHECKING:
    from ..context import AppContext


def build_habits_view(ctx: AppContext, page: ft.Page) -> ft.View:
    """Build the habits view."""

    uid = ctx.require_user_id()
    habit_list_ref = ft.Ref[ft.Column]()
    archived_list_ref = ft.Ref[ft.Column]()
    heatmap_ref = ft.Ref[ft.GridView]()
    selected_ref = ft.Ref[ft.Text]()
    streak_ref = ft.Ref[ft.Text]()
    longest_ref = ft.Ref[ft.Text]()
    reminder_ref = ft.Ref[ft.Text]()
    heatmap_label_ref = ft.Ref[ft.Text]()
    selected_habit: int | None = None
    show_archived_checkbox = ft.Checkbox(label="Show archived", value=False)
    heatmap_days = ft.Dropdown(
        label="Heatmap window",
        options=[
            ft.dropdown.Option("28", "Last 28 days"),
            ft.dropdown.Option("90", "Last 90 days"),
            ft.dropdown.Option("180", "Last 180 days"),
        ],
        value="90",
        width=180,
    )

    def _window_days() -> int:
        """Return the selected heatmap window as an int with fallback."""

        raw = heatmap_days.value
        try:
            return int(raw) if raw is not None else 90
        except (TypeError, ValueError):
            dev_log(ctx.config, "Invalid heatmap window value", context={"value": raw})
            return 90

    def _validate_reminder(raw: str | None) -> str | None:
        """Return HH:MM string when valid, otherwise None."""
        if not raw:
            return None
        try:
            datetime.strptime(raw.strip(), "%H:%M")
            return raw.strip()
        except ValueError:
            return None

    def render_heatmap(habit_id: int, days: int | None = None):
        window = days if days is not None else _window_days()
        today = date.today()
        start = today - timedelta(days=window - 1)
        entries = ctx.habit_repo.get_entries_for_habit(habit_id, start, today, user_id=uid)
        completed = {e.occurred_on for e in entries if e.value > 0}
        cells: list[ft.Control] = []
        day = start
        max_count = max(1, len(completed))
        while day <= today:
            is_done = day in completed
            # Intensity mapping for streak-ish visualization: darker for recent wins
            recency_factor = max(0.2, 1 - (today - day).days / window)
            alpha = 0.15 + (0.85 * recency_factor if is_done else 0.0)
            color = ft.Colors.GREEN if is_done else ft.Colors.SURFACE_CONTAINER_HIGHEST
            cells.append(
                ft.Container(
                    width=18,
                    height=18,
                    bgcolor=color,
                    opacity=alpha if is_done else 1.0,
                    border_radius=3,
                    tooltip=f"{day.isoformat()} {'✅' if is_done else '•'}",
                )
            )
            day += timedelta(days=1)
        # Pad grid to a full week rows for nicer alignment
        remainder = len(cells) % 7
        if remainder:
            for _ in range(7 - remainder):
                cells.append(ft.Container(width=18, height=18, bgcolor=ft.Colors.GREY_300))
        if heatmap_ref.current:
            heatmap_ref.current.controls = cells
            if getattr(heatmap_ref.current, "page", None):
                heatmap_ref.current.update()
        if heatmap_label_ref.current:
            heatmap_label_ref.current.value = f"Last {window} days"
            if getattr(heatmap_label_ref.current, "page", None):
                heatmap_label_ref.current.update()

    def select_habit(hid: int, name: str):
        nonlocal selected_habit
        selected_habit = hid
        selected_ref.current.value = name
        streak_ref.current.value = (
            f"Current streak: {ctx.habit_repo.get_current_streak(hid, user_id=uid)}"
        )
        longest_ref.current.value = (
            f"Longest streak: {ctx.habit_repo.get_longest_streak(hid, user_id=uid)}"
        )
        habit_obj = ctx.habit_repo.get_by_id(hid, user_id=uid)
        if reminder_ref.current and habit_obj:
            reminder_ref.current.value = reminder_placeholder(habit_obj)
            if getattr(reminder_ref.current, "page", None):
                reminder_ref.current.update()
        # Update detail chips for completion meta
        if habit_obj:
            completed = ctx.habit_repo.get_entry(hid, date.today(), user_id=uid) is not None
            selected_ref.current.value = (
                f"{habit_obj.name} ({'done today' if completed else 'not done today'})"
            )
        render_heatmap(hid)
        page.update()

    def refresh_habit_list(show_archived: bool = False):
        habits = ctx.habit_repo.list_active(user_id=uid)
        archived = ctx.habit_repo.list_all(user_id=uid, include_inactive=True)
        archived = [h for h in archived if not h.is_active]
        today = date.today()

        def _toggle_habit(habit_id: int):
            entry = ctx.habit_repo.get_entry(habit_id, today, user_id=uid)
            if entry:
                ctx.habit_repo.delete_entry(habit_id, today, user_id=uid)
                dev_log(ctx.config, "Habit unchecked", context={"habit_id": habit_id})
            else:
                ctx.habit_repo.upsert_entry(
                    HabitEntry(habit_id=habit_id, occurred_on=today, value=1, user_id=uid),
                    user_id=uid,
                )
                dev_log(ctx.config, "Habit completed", context={"habit_id": habit_id})
            refresh_habit_list(show_archived)
            if selected_habit == habit_id:
                habit_obj = ctx.habit_repo.get_by_id(habit_id, user_id=uid)
                if habit_obj:
                    select_habit(habit_id, habit_obj.name)
            page.snack_bar = ft.SnackBar(content=ft.Text("Habit updated"))
            page.snack_bar.open = True
            page.update()

        def _archive(habit_id: int, is_active: bool):
            rec = ctx.habit_repo.get_by_id(habit_id, user_id=uid)
            if rec:
                rec.is_active = is_active
                ctx.habit_repo.update(rec, user_id=uid)
                dev_log(
                    ctx.config,
                    "Habit status changed",
                    context={"habit_id": habit_id, "active": is_active},
                )
            refresh_habit_list(show_archived)
            page.snack_bar = ft.SnackBar(
                content=ft.Text("Habit reactivated" if is_active else "Habit archived")
            )
            page.snack_bar.open = True
            page.update()

        def _edit(habit: Habit):
            open_create_dialog(None, habit=habit)

        rows: list[ft.Control] = []
        for habit in habits:
            current_streak = ctx.habit_repo.get_current_streak(habit.id, user_id=uid)
            longest_streak = ctx.habit_repo.get_longest_streak(habit.id, user_id=uid)
            today_entry = ctx.habit_repo.get_entry(habit.id, today, user_id=uid)
            is_completed = today_entry is not None and today_entry.value > 0
            streak_label = f"Current: {current_streak} / Longest: {longest_streak}"

            rows.append(
                ft.Card(
                    content=ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Switch(
                                    value=is_completed,
                                    on_change=lambda _e, hid=habit.id: _toggle_habit(hid),
                                ),
                                ft.Column(
                                    controls=[
                                        ft.Text(habit.name, size=16, weight=ft.FontWeight.BOLD),
                                        ft.Text(
                                            habit.description or "No description",
                                            size=12,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                        ft.Text(
                                            streak_label,
                                            size=12,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                    ],
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.EDIT,
                                    tooltip="Edit",
                                    on_click=lambda _e, h=habit: _edit(h),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.ARCHIVE_OUTLINED,
                                    tooltip="Archive habit",
                                    on_click=lambda _e, hid=habit.id: _archive(hid, False),
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
                        controls=[
                            ft.Icon(
                                ft.Icons.CHECK_CIRCLE_OUTLINE,
                                size=64,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.Text("No active habits", size=20, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Create your first habit to start tracking",
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    ),
                    padding=24,
                )
            )

        habit_list_ref.current.controls = rows

        archived_rows: list[ft.Control] = []
        if show_archived and archived:
            # Add section header
            archived_rows.append(
                ft.Container(
                    content=ft.Text(
                        "Archived Habits",
                        size=16,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    padding=ft.padding.only(top=16, bottom=8),
                )
            )
            for habit in archived:
                archived_rows.append(
                    ft.Container(
                        content=ft.Row(
                            controls=[
                                ft.Column(
                                    controls=[
                                        ft.Text(habit.name, weight=ft.FontWeight.W_500),
                                        ft.Text(
                                            habit.description or "No description",
                                            size=12,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                    ],
                                    expand=True,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.UNARCHIVE,
                                    tooltip="Reactivate habit",
                                    on_click=lambda _e, hid=habit.id: _archive(hid, True),
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        padding=12,
                        bgcolor=ft.Colors.SURFACE,
                        border_radius=8,
                    )
                )
        elif show_archived:
            archived_rows.append(
                ft.Container(
                    content=ft.Text(
                        "No archived habits",
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        italic=True,
                    ),
                    padding=16,
                )
            )

        if archived_list_ref.current is not None:
            archived_list_ref.current.controls = archived_rows
            if getattr(archived_list_ref.current, "page", None):
                archived_list_ref.current.update()

        page.update()

    show_archived_checkbox.on_change = lambda _e: refresh_habit_list(show_archived_checkbox.value)

    habit_list = ft.Column(ref=habit_list_ref, spacing=8)
    habit_list_ref.current = habit_list
    archived_list = ft.Column(ref=archived_list_ref, spacing=4)

    heatmap = ft.GridView(
        ref=heatmap_ref,
        runs_count=7,
        max_extent=24,
        child_aspect_ratio=1.0,
        spacing=4,
        run_spacing=4,
        expand=True,
    )

    def _on_heatmap_change(e):
        if selected_habit is not None:
            render_heatmap(selected_habit)

    heatmap_days.on_change = _on_heatmap_change

    detail_panel = ft.Column(
        controls=[
            ft.Text("Habit detail", size=16, weight=ft.FontWeight.BOLD),
            ft.Text("", ref=selected_ref, size=20, weight=ft.FontWeight.BOLD),
            ft.Text("", ref=streak_ref),
            ft.Text("", ref=longest_ref),
            ft.Text("", ref=reminder_ref, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
            ft.Text("", ref=heatmap_label_ref, weight=ft.FontWeight.BOLD),
            ft.Row(controls=[heatmap_days], alignment=ft.MainAxisAlignment.START),
            heatmap,
        ],
        spacing=8,
        expand=True,
    )

    def _close_dialog(dialog: ft.AlertDialog) -> None:
        """Helper to properly close a dialog."""
        dialog.open = False
        page.update()

    def open_create_dialog(_=None, *, habit: Habit | None = None):
        """Open habit creation/editing dialog using reusable component."""
        def on_save():
            """Callback after habit is saved."""
            refresh_habit_list(show_archived_checkbox.value)
            if habit:
                select_habit(habit.id, habit.name)

        show_habit_dialog(
            ctx=ctx,
            page=page,
            habit=habit,
            on_save_callback=on_save,
        )

    # Kept for backward compatibility - remove in future cleanup
    def _old_open_create_dialog(_=None, *, habit: Habit | None = None):
        is_edit = habit is not None
        name_field = ft.TextField(
            label="Name",
            width=260,
            autofocus=True,
            value=habit.name if habit else "",
        )
        desc_field = ft.TextField(
            label="Description",
            width=260,
            helper_text="Optional: why this habit matters.",
            value=habit.description if habit else "",
        )
        cadence_field = ft.Dropdown(
            label="Cadence",
            options=[ft.dropdown.Option(key, label) for key, label in HABIT_CADENCE_OPTIONS],
            value=habit.cadence if habit else "daily",
            width=200,
        )

        reminder_time = ft.TextField(
            label="Reminder time (HH:MM)",
            width=160,
            hint_text="08:00",
            value=habit.reminder_time if habit else "",
        )

        def save_habit(_):
            if not name_field.value or not name_field.value.strip():
                name_field.error_text = "Name is required"
                name_field.update()
                return
            name_field.error_text = None
            reminder_value = _validate_reminder(reminder_time.value)
            if reminder_time.value and not reminder_value:
                reminder_time.error_text = "Use HH:MM format"
                reminder_time.update()
                return
            reminder_time.error_text = None
            selected_id: int | None = None
            selected_name: str | None = None
            try:
                if is_edit and habit:
                    habit.name = name_field.value.strip()
                    habit.description = desc_field.value or ""
                    habit.cadence = cadence_field.value or "daily"
                    habit.reminder_time = reminder_value
                    ctx.habit_repo.update(habit, user_id=uid)
                    dev_log(ctx.config, "Habit updated", context={"name": habit.name})
                    selected_id = habit.id
                    selected_name = habit.name
                else:
                    new_habit = Habit(
                        name=name_field.value.strip(),
                        description=desc_field.value or "",
                        cadence=cadence_field.value or "daily",
                        reminder_time=reminder_value,
                        user_id=uid,
                    )
                    created = ctx.habit_repo.create(new_habit, user_id=uid)
                    selected_id = created.id
                    selected_name = created.name
                    dev_log(ctx.config, "Habit created", context={"name": new_habit.name})
                dialog.open = False
                refresh_habit_list(show_archived_checkbox.value)
                if selected_id and selected_name:
                    select_habit(selected_id, selected_name)
                page.snack_bar = ft.SnackBar(
                    content=ft.Text("Habit updated" if is_edit else "Habit created")
                )
                page.snack_bar.open = True
                page.update()
            except Exception as exc:
                dev_log(ctx.config, "Habit save failed", exc=exc)
                page.snack_bar = ft.SnackBar(content=ft.Text(f"Failed to save: {exc}"))
                page.snack_bar.open = True
                page.update()

        dialog = ft.AlertDialog(
            title=ft.Text("Edit habit" if is_edit else "Create habit"),
            content=ft.Column(
                controls=[name_field, desc_field, cadence_field, reminder_time],
                tight=True,
                spacing=8,
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: _close_dialog(dialog)),
                ft.FilledButton("Save", on_click=save_habit),
            ],
        )
        page.dialog = dialog
        dialog.open = True
        page.update()

    refresh_habit_list()
    active = ctx.habit_repo.list_active(user_id=uid)
    if active:
        select_habit(active[0].id, active[0].name)

    content = ft.Row(
        controls=[
            ft.Column(
                controls=[
                    ft.Row(
                        controls=[
                            ft.Text("Habits", size=24, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                date.today().strftime("%A, %B %d, %Y"),
                                color=ft.Colors.ON_SURFACE_VARIANT,
                            ),
                            ft.FilledButton(
                                "Add habit",
                                icon=ft.Icons.ADD,
                                on_click=lambda _: controllers.navigate(page, '/add-data'),
                            ),
                        ],
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    ),
                    ft.Container(height=8),
                    habit_list,
                    ft.Container(height=12),
                    ft.Row(
                        controls=[
                            show_archived_checkbox,
                            ft.Text("Archived habits", weight=ft.FontWeight.BOLD),
                        ],
                        alignment=ft.MainAxisAlignment.START,
                        spacing=8,
                    ),
                    archived_list,
                    ft.Container(height=80),  # Add bottom padding buffer to prevent overlap
                ],
                expand=True,
                scroll=ft.ScrollMode.AUTO,  # Make entire left column scrollable
            ),
            ft.VerticalDivider(width=1),
            ft.Container(content=detail_panel, width=320, padding=12),
        ],
        expand=True,
    )

    app_bar = build_app_bar(ctx, "Habits", page)
    main_layout = build_main_layout(ctx, page, "/habits", content, use_menu_bar=True)

    return ft.View(
        route="/habits",
        appbar=app_bar,
        controls=main_layout,
        padding=0,
    )

"""Habit creation and editing dialogs (FR-15).

Implements CRUD for habits with validation:
- Create new habit
- Edit existing habit  
- Validate form inputs (name required, time format)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import flet as ft

from ....logging_config import get_logger
from ....models.habit import Habit

if TYPE_CHECKING:
    from ...context import AppContext

logger = get_logger(__name__)


def show_habit_dialog(
    ctx: AppContext,
    page: ft.Page,
    habit: Habit | None = None,
    on_save_callback=None,
) -> None:
    """Show create or edit habit dialog.

    Args:
        ctx: Application context
        page: Flet page
        habit: Existing habit to edit, or None to create new
        on_save_callback: Optional callback function to call after successful save
    """
    is_edit = habit is not None
    uid = ctx.require_user_id()

    # Form fields
    name_field = ft.TextField(
        label="Habit Name *",
        value=habit.name if habit else "",
        hint_text="e.g., Exercise, Read, Meditate",
        autofocus=True,
        max_length=100,
        width=400,
    )

    description_field = ft.TextField(
        label="Description (optional)",
        value=habit.description if habit else "",
        hint_text="Why is this habit important to you?",
        multiline=True,
        min_lines=2,
        max_lines=4,
        width=400,
    )

    reminder_time_field = ft.TextField(
        label="Reminder Time (optional)",
        value=habit.reminder_time if habit and habit.reminder_time else "",
        hint_text="HH:MM (24-hour format, e.g., 09:00 or 18:30)",
        width=200,
    )

    cadence_field = ft.Dropdown(
        label="Frequency",
        options=[
            ft.dropdown.Option("daily", "Daily"),
            # Future: weekly, custom
        ],
        value=habit.cadence if habit else "daily",
        width=200,
    )

    def _validate_time_format(time_str: str) -> bool:
        """Validate HH:MM time format."""
        if not time_str:
            return True  # Empty is OK
        try:
            parts = time_str.split(":")
            if len(parts) != 2:
                return False
            hour, minute = int(parts[0]), int(parts[1])
            return 0 <= hour <= 23 and 0 <= minute <= 59
        except (ValueError, IndexError):
            return False

    def _validate_and_save(_):
        """Validate form and save habit."""
        # Clear previous errors
        name_field.error_text = None
        reminder_time_field.error_text = None

        # Validate name
        name = (name_field.value or "").strip()
        if not name:
            name_field.error_text = "Name is required"
            name_field.update()
            return

        if len(name) > 100:
            name_field.error_text = "Name must be 100 characters or less"
            name_field.update()
            return

        # Validate reminder time format
        reminder_time = (reminder_time_field.value or "").strip() or None
        if reminder_time and not _validate_time_format(reminder_time):
            reminder_time_field.error_text = "Use HH:MM format (e.g., 09:00)"
            reminder_time_field.update()
            return

        description = (description_field.value or "").strip() or None
        cadence = cadence_field.value or "daily"

        # Save habit
        try:
            if is_edit:
                # Update existing
                habit.name = name
                habit.description = description
                habit.reminder_time = reminder_time
                habit.cadence = cadence
                updated = ctx.habit_repo.update(habit, user_id=uid)
                logger.info(f"Habit updated: {updated.name}")
                message = f"Habit '{name}' updated"
            else:
                # Create new
                new_habit = Habit(
                    name=name,
                    description=description,
                    reminder_time=reminder_time,
                    cadence=cadence,
                    is_active=True,
                    user_id=uid,
                )
                created = ctx.habit_repo.create(new_habit, user_id=uid)
                logger.info(f"Habit created: {created.name}")
                message = f"Habit '{name}' created"

            # Close dialog
            dialog.open = False
            page.dialog = None
            page.update()

            # Show success message
            page.snack_bar = ft.SnackBar(content=ft.Text(message))
            page.snack_bar.open = True
            page.update()

            # Call callback if provided
            if on_save_callback:
                on_save_callback()

        except Exception as exc:
            logger.error(f"Failed to save habit: {exc}", exc_info=True)
            page.snack_bar = ft.SnackBar(
                content=ft.Text(f"Failed to save: {exc}"),
                bgcolor=ft.Colors.ERROR,
            )
            page.snack_bar.open = True
            page.update()

    def _close_dialog(_):
        """Close the dialog without saving."""
        dialog.open = False
        page.dialog = None
        page.update()

    # Build dialog
    dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Edit Habit" if is_edit else "New Habit"),
        content=ft.Column(
            controls=[
                ft.Text(
                    "Track daily habits to build better routines and see your progress.",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
                ft.Divider(),
                name_field,
                description_field,
                ft.Row(
                    controls=[cadence_field, reminder_time_field],
                    spacing=10,
                ),
                ft.Text(
                    "Reminders are optional. Leave blank if you don't want notifications.",
                    size=11,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                    italic=True,
                ),
            ],
            tight=True,
            spacing=12,
            width=450,
        ),
        actions=[
            ft.TextButton("Cancel", on_click=_close_dialog),
            ft.FilledButton("Save", on_click=_validate_and_save),
        ],
    )

    page.dialog = dialog
    dialog.open = True
    page.update()

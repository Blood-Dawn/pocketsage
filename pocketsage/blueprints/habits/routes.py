"""Habit routes."""

from __future__ import annotations

from datetime import date, timedelta

from flask import flash, redirect, render_template, url_for
from sqlmodel import select

from . import bp
from ...extensions import session_scope
from ...models.habit import Habit, HabitEntry


def _compute_streak(entries: list[HabitEntry]) -> int:
    """Return the current streak length for the provided habit entries."""

    if not entries:
        return 0

    today = date.today()
    latest_entry = entries[0].occurred_on

    if today - latest_entry > timedelta(days=1):
        return 0

    streak = 1
    previous_day = latest_entry
    for entry in entries[1:]:
        if entry.occurred_on == previous_day - timedelta(days=1):
            streak += 1
            previous_day = entry.occurred_on
        else:
            break
    return streak


@bp.get("/")
def list_habits():
    """Show habits overview and current streaks."""

    # TODO(@habits-squad): populate context with repository results + streak calculations.
    habits: list = []

    show_empty_state = len(habits) == 0

    return render_template(
        "habits/index.html",
        habits=habits,
        show_empty_state=show_empty_state,
    )


@bp.post("/<int:habit_id>/toggle")
def toggle_habit(habit_id: int):
    """Toggle habit completion state for today."""

    # TODO(@habits-squad): record HabitEntry for current date via repository layer.
    today = date.today()
    flash(f"Habit toggle queued for {today:%Y-%m-%d}", "info")
    return redirect(url_for("habits.list_habits"))


@bp.get("/new")
def new_habit():
    """Render form for creating a new habit."""

    # TODO(@habits-squad): supply HabitForm with defaults.
    return render_template("habits/form.html")

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

    with session_scope() as session:
        result = session.exec(
            select(Habit).where(Habit.is_active == True).order_by(Habit.name)  # noqa: E712
        )
        habits = result.all()

        summaries: list[dict] = []
        for habit in habits:
            entries = session.exec(
                select(HabitEntry)
                .where(HabitEntry.habit_id == habit.id)
                .order_by(HabitEntry.occurred_on.desc())
            ).all()

            last_completed = entries[0].occurred_on if entries else None
            streak = _compute_streak(entries)
            goal_text = habit.description.strip() or f"{habit.cadence.title()} habit"

            streak_state = "muted"
            if last_completed is not None:
                if last_completed == date.today():
                    streak_state = "success"
                else:
                    streak_state = "danger"

            summaries.append(
                {
                    "id": habit.id,
                    "name": habit.name,
                    "goal": goal_text,
                    "cadence": habit.cadence.title(),
                    "streak": streak if entries else 0,
                    "streak_state": streak_state,
                    "last_completed": last_completed,
                    "last_completed_display": (
                        last_completed.strftime("%b %d, %Y") if last_completed else "—"
                    ),
                }
            )

    return render_template("habits/index.html", habits=summaries)


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

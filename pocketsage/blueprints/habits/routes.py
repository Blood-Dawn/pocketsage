"""Habit routes."""

from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, request, url_for

from . import bp


@bp.get("/")
def list_habits():
    """Show habits overview and current streaks."""

    # TODO(@habits-squad): populate context with repository results + streak calculations.
    return render_template("habits/index.html")


@bp.post("/<int:habit_id>/toggle")
def toggle_habit(habit_id: int):
    """Toggle habit completion state for today."""

    # TODO(@habits-squad): record HabitEntry for current date via repository layer.
    today = date.today()
    target_state = request.form.get("target_state", "complete")

    if target_state == "complete":
        flash(
            f"Marked habit #{habit_id} complete for {today:%Y-%m-%d}.",
            "success",
        )
    elif target_state == "undo":
        flash(
            f"Reopened habit #{habit_id} for {today:%Y-%m-%d}.",
            "info",
        )
    else:
        flash(
            "We couldn't process that habit update. Please try again.",
            "warning",
        )
    return redirect(url_for("habits.list_habits"))


@bp.get("/new")
def new_habit():
    """Render form for creating a new habit."""

    # TODO(@habits-squad): supply HabitForm with defaults.
    return render_template("habits/form.html")

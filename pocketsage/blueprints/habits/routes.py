"""Habit routes."""

from __future__ import annotations

from datetime import date, time

from flask import flash, redirect, render_template, request, url_for

from . import bp
from .forms import HabitCadence, HabitForm


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
    flash(f"Habit toggle queued for {today:%Y-%m-%d}", "info")
    return redirect(url_for("habits.list_habits"))


@bp.route("/new", methods=("GET", "POST"))
def new_habit():
    """Render form for creating a new habit."""

    form = HabitForm()
    errors: dict[str, list[str]] = {}
    if request.method == "POST":
        custom_interval_raw = request.form.get("custom_interval_days", "").strip()
        reminder_time_raw = request.form.get("reminder_time", "").strip()
        payload = {
            "name": request.form.get("name", ""),
            "description": request.form.get("description", ""),
            "cadence": request.form.get("cadence", HabitCadence.DAILY.value),
            "custom_interval_days": custom_interval_raw or None,
            "reminders_enabled": "reminders_enabled" in request.form,
            "reminder_time": None,
            "tags": request.form.get("tags", ""),
        }

        if reminder_time_raw:
            try:
                payload["reminder_time"] = time.fromisoformat(reminder_time_raw)
            except ValueError:
                payload["reminder_time"] = None

        form = HabitForm.model_construct(**payload)
        errors = form.validation_errors()
        if not errors:
            flash("Habit saved! Tracking will be added soon.", "success")
            return redirect(url_for("habits.list_habits"))

    cadence_options = list(HabitCadence)
    return render_template(
        "habits/form.html", form=form, cadence_options=cadence_options, errors=errors
    )

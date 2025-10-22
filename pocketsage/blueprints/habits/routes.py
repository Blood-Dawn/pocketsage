"""Habit routes."""

from __future__ import annotations

from datetime import date

from flask import flash, redirect, render_template, url_for

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


@bp.get("/new")
def new_habit():
    """Render form for creating a new habit."""

    form = HabitForm()
    cadence_options = list(HabitCadence)
    return render_template("habits/form.html", form=form, cadence_options=cadence_options)

"""Habit routes."""

from __future__ import annotations

from datetime import date, time, timedelta

from flask import flash, redirect, render_template, request, url_for

from ...extensions import session_scope
from . import bp
from .forms import HabitCadence, HabitForm
from .repository import SqlModelHabitsRepository

# Constants for habit tracking
HISTORY_DAYS = 30  # Number of days to show in habit history
STREAK_LOOKBACK_DAYS = 7  # Number of days to consider for streak calculation


@bp.get("/")
def list_habits():
    """Show habits overview and current streaks."""

    today = date.today()
    history_start = today - timedelta(days=HISTORY_DAYS - 1)
    streak_window_start = today - timedelta(days=STREAK_LOOKBACK_DAYS - 1)
    fetch_since = min(history_start, streak_window_start)

    with session_scope() as session:
        repo = SqlModelHabitsRepository(session)
        raw_habits = list(repo.list_habits())
        habit_ids = [habit.id for habit in raw_habits if habit.id is not None]
        entries = repo.recent_entries(habit_ids=habit_ids, since=fetch_since)

        entries_by_habit: dict[int, list] = {habit_id: [] for habit_id in habit_ids}
        for entry in entries:
            entries_by_habit.setdefault(entry.habit_id, []).append(entry)
        for habit_entries in entries_by_habit.values():
            habit_entries.sort(key=lambda item: item.occurred_on)

        habits_view: list[dict] = []
        for habit in raw_habits:
            if habit.id is None:
                continue

            habit_entries = entries_by_habit.get(habit.id, [])
            completion_dates = {entry.occurred_on for entry in habit_entries}
            history: list[dict] = []
            for index in range(HISTORY_DAYS):
                day = history_start + timedelta(days=index)
                history.append(
                    {
                        "date": day.isoformat(),
                        "label": day.strftime("%b %d").replace(" 0", " "),
                        "weekday": day.strftime("%a"),
                        "completed": day in completion_dates,
                    }
                )

            weekly_totals: list[dict] = []
            for offset in range(0, len(history), 7):
                bucket = history[offset : offset + 7]
                if not bucket:
                    continue
                week_start = date.fromisoformat(bucket[0]["date"])
                completed = sum(1 for day in bucket if day["completed"])
                weekly_totals.append(
                    {
                        "label": f"Week of {week_start.strftime('%b %d').replace(' 0', ' ')}",
                        "start_date": bucket[0]["date"],
                        "completed": completed,
                        "total": len(bucket),
                    }
                )

            streak = 0
            check_day = today
            while check_day >= fetch_since and check_day in completion_dates:
                streak += 1
                check_day -= timedelta(days=1)

            last_week = history[-7:]
            completed_last_week = sum(1 for day in last_week if day["completed"])
            summary = f"{streak} day streak · {completed_last_week} of last 7 days completed"

            habits_view.append(
                {
                    "id": habit.id,
                    "name": habit.name,
                    "description": habit.description,
                    "streak": streak,
                    "history": history,
                    "weekly_totals": weekly_totals,
                    "summary": summary,
                    "completed_days": sum(1 for day in history if day["completed"]),
                    "history_start": history_start.isoformat(),
                    "history_end": today.isoformat(),
                }
            )

    return render_template(
        "habits/index.html",
        habits=habits_view,
        history_days=HISTORY_DAYS,
        history_start=history_start,
        history_end=today,
    )


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

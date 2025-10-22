"""Habit routes."""

from __future__ import annotations

from datetime import date, timedelta

from flask import flash, redirect, render_template, url_for

from ...extensions import session_scope
from . import bp
from .repository import SqlModelHabitsRepository


HISTORY_DAYS = 21
STREAK_LOOKBACK_DAYS = 60


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
        summary = (
            f"{streak} day streak · {completed_last_week} of last 7 days completed"
        )

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
    flash(f"Habit toggle queued for {today:%Y-%m-%d}", "info")
    return redirect(url_for("habits.list_habits"))


@bp.get("/new")
def new_habit():
    """Render form for creating a new habit."""

    # TODO(@habits-squad): supply HabitForm with defaults.
    return render_template("habits/form.html")

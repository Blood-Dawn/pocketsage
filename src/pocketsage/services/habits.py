"""Habit service helpers for streaks and reminders (placeholder)."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Iterable

from ..models.habit import Habit, HabitEntry


def compute_streaks(entries: Iterable[HabitEntry], *, today: date | None = None) -> tuple[int, int]:
    """Return (current_streak, longest_streak) from a collection of entries."""

    today = today or date.today()
    by_day = {e.occurred_on: e for e in entries if e.value > 0}

    # Current streak: walk backwards from today until a gap.
    current = 0
    cursor = today
    while cursor in by_day:
        current += 1
        cursor -= timedelta(days=1)

    # Longest streak: sweep through sorted days, counting consecutive runs.
    days = sorted(by_day.keys())
    longest = 0
    run = 0
    last_day: date | None = None
    for d in days:
        if last_day is None or d == last_day + timedelta(days=1):
            run += 1
        else:
            longest = max(longest, run)
            run = 1
        last_day = d
    longest = max(longest, run)

    return current, longest


def reminder_placeholder(habit: Habit) -> str:
    """Return a placeholder note for reminders until notifications are implemented."""

    if habit.reminder_time:
        return f"Reminder set for {habit.reminder_time} (no-op placeholder)"
    return "Reminders not configured"


__all__ = ["compute_streaks", "reminder_placeholder"]

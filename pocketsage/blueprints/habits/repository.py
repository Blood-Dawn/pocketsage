"""Habits repository interfaces."""

from __future__ import annotations

from datetime import date
from typing import Iterable, Protocol

from ...models.habit import Habit, HabitEntry


class HabitsRepository(Protocol):
    """Persistence contract for habit operations."""

    def list_habits(self) -> Iterable[Habit]:  # pragma: no cover - interface
        ...

    def record_entry(
        self, *, habit_id: int, occurred_on: date
    ) -> HabitEntry:  # pragma: no cover - interface
        ...

    def create_habit(self, *, payload: dict) -> Habit:  # pragma: no cover - interface
        ...


# TODO(@data-squad): implement SQL-backed repository for habits blueprint.

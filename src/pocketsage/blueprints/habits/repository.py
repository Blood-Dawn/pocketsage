"""Habits repository interfaces."""

from __future__ import annotations

from datetime import date
from typing import Iterable, Protocol, Sequence

from sqlmodel import Session, select

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


class SqlModelHabitsRepository:
    """SQLModel-backed habits repository."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def list_habits(self) -> list[Habit]:
        statement = (
            select(Habit)
            .where(Habit.is_active == True)  # noqa: E712 - SQLAlchemy comparison
            .order_by(Habit.name.asc())
        )
        return list(self.session.exec(statement).all())

    def recent_entries(
        self, *, habit_ids: Sequence[int], since: date
    ) -> list[HabitEntry]:
        if not habit_ids:
            return []

        statement = (
            select(HabitEntry)
            .where(HabitEntry.habit_id.in_(habit_ids))
            .where(HabitEntry.occurred_on >= since)
            .order_by(HabitEntry.occurred_on.asc())
        )
        return list(self.session.exec(statement).all())


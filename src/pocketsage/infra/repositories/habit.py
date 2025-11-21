"""SQLModel implementation of Habit repository."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Callable, Optional

from sqlmodel import Session, select

from ...models.habit import Habit, HabitEntry


class SQLModelHabitRepository:
    """SQLModel-based habit repository implementation."""

    def __init__(self, session_factory: Callable[[], Session]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    def get_by_id(self, habit_id: int, *, user_id: int) -> Optional[Habit]:
        """Retrieve a habit by ID."""
        with self.session_factory() as session:
            obj = session.exec(
                select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
            ).first()
            if obj:
                session.expunge(obj)
            return obj

    def get_by_name(self, name: str, *, user_id: int) -> Optional[Habit]:
        """Retrieve a habit by name."""
        with self.session_factory() as session:
            statement = select(Habit).where(Habit.name == name, Habit.user_id == user_id)
            obj = session.exec(statement).first()
            if obj:
                session.expunge(obj)
            return obj

    def list_all(self, *, user_id: int, include_inactive: bool = False) -> list[Habit]:
        """List all habits, optionally including inactive ones."""
        with self.session_factory() as session:
            statement = (
                select(Habit).where(Habit.user_id == user_id).order_by(Habit.name)  # type: ignore
            )

            if not include_inactive:
                statement = statement.where(Habit.is_active == True)  # noqa: E712

            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def list_active(self, *, user_id: int) -> list[Habit]:
        """List only active habits."""
        return self.list_all(user_id=user_id, include_inactive=False)

    def create(self, habit: Habit, *, user_id: int) -> Habit:
        """Create a new habit."""
        with self.session_factory() as session:
            habit.user_id = user_id
            session.add(habit)
            session.commit()
            session.refresh(habit)
            session.expunge(habit)
            return habit

    def update(self, habit: Habit, *, user_id: int) -> Habit:
        """Update an existing habit."""
        with self.session_factory() as session:
            habit.user_id = user_id
            session.add(habit)
            session.commit()
            session.refresh(habit)
            session.expunge(habit)
            return habit

    def delete(self, habit_id: int, *, user_id: int) -> None:
        """Delete a habit by ID."""
        with self.session_factory() as session:
            habit = session.exec(
                select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
            ).first()
            if habit:
                session.delete(habit)
                session.commit()

    # Habit entry operations
    def get_entry(self, habit_id: int, occurred_on: date, *, user_id: int) -> Optional[HabitEntry]:
        """Get a specific habit entry."""
        with self.session_factory() as session:
            statement = (
                select(HabitEntry)
                .where(HabitEntry.user_id == user_id)
                .where(HabitEntry.habit_id == habit_id)
                .where(HabitEntry.occurred_on == occurred_on)
            )
            obj = session.exec(statement).first()
            if obj:
                session.expunge(obj)
            return obj

    def get_entries_for_habit(
        self, habit_id: int, start_date: date, end_date: date, *, user_id: int
    ) -> list[HabitEntry]:
        """Get entries for a habit within a date range."""
        with self.session_factory() as session:
            statement = (
                select(HabitEntry)
                .where(HabitEntry.user_id == user_id)
                .where(HabitEntry.habit_id == habit_id)
                .where(HabitEntry.occurred_on >= start_date)
                .where(HabitEntry.occurred_on <= end_date)
                .order_by(HabitEntry.occurred_on)  # type: ignore
            )
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def upsert_entry(self, entry: HabitEntry, *, user_id: int) -> HabitEntry:
        """Insert or update a habit entry."""
        with self.session_factory() as session:
            entry.user_id = user_id
            existing = session.exec(
                select(HabitEntry)
                .where(HabitEntry.user_id == user_id)
                .where(HabitEntry.habit_id == entry.habit_id)
                .where(HabitEntry.occurred_on == entry.occurred_on)
            ).first()

            if existing:
                existing.value = entry.value
                session.add(existing)
                session.commit()
                session.refresh(existing)
                session.expunge(existing)
                return existing
            else:
                session.add(entry)
                session.commit()
                session.refresh(entry)
                session.expunge(entry)
                return entry

    def delete_entry(self, habit_id: int, occurred_on: date, *, user_id: int) -> None:
        """Delete a habit entry."""
        with self.session_factory() as session:
            entry = session.exec(
                select(HabitEntry)
                .where(HabitEntry.user_id == user_id)
                .where(HabitEntry.habit_id == habit_id)
                .where(HabitEntry.occurred_on == occurred_on)
            ).first()

            if entry:
                session.delete(entry)
                session.commit()

    def get_current_streak(self, habit_id: int, *, user_id: int) -> int:
        """Calculate current streak for a habit."""
        with self.session_factory() as session:
            today = date.today()
            streak = 0

            # Start from today and work backwards
            current_date = today
            while True:
                statement = (
                    select(HabitEntry)
                    .where(HabitEntry.user_id == user_id)
                    .where(HabitEntry.habit_id == habit_id)
                    .where(HabitEntry.occurred_on == current_date)
                )
                entry = session.exec(statement).first()

                if entry and entry.value > 0:
                    streak += 1
                    current_date -= timedelta(days=1)
                else:
                    break

            return streak

    def get_longest_streak(self, habit_id: int, *, user_id: int) -> int:
        """Calculate longest streak for a habit."""
        with self.session_factory() as session:
            statement = (
                select(HabitEntry)
                .where(HabitEntry.user_id == user_id)
                .where(HabitEntry.habit_id == habit_id)
                .where(HabitEntry.value > 0)
                .order_by(HabitEntry.occurred_on)  # type: ignore
            )
            entries = list(session.exec(statement).all())

            if not entries:
                return 0

            max_streak = 1
            current_streak = 1

            for i in range(1, len(entries)):
                expected_date = entries[i - 1].occurred_on + timedelta(days=1)
                if entries[i].occurred_on == expected_date:
                    current_streak += 1
                    max_streak = max(max_streak, current_streak)
                else:
                    current_streak = 1

            return max_streak

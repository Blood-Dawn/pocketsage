"""Habit repository protocol."""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol

from ...models.habit import Habit, HabitEntry


class HabitRepository(Protocol):
    """Repository for managing habit entities."""

    def get_by_id(self, habit_id: int) -> Optional[Habit]:
        """Retrieve a habit by ID."""
        ...

    def get_by_name(self, name: str) -> Optional[Habit]:
        """Retrieve a habit by name."""
        ...

    def list_all(self, include_inactive: bool = False) -> list[Habit]:
        """List all habits, optionally including inactive ones."""
        ...

    def list_active(self) -> list[Habit]:
        """List only active habits."""
        ...

    def create(self, habit: Habit) -> Habit:
        """Create a new habit."""
        ...

    def update(self, habit: Habit) -> Habit:
        """Update an existing habit."""
        ...

    def delete(self, habit_id: int) -> None:
        """Delete a habit by ID."""
        ...

    # Habit entry operations
    def get_entry(self, habit_id: int, occurred_on: date) -> Optional[HabitEntry]:
        """Get a specific habit entry."""
        ...

    def get_entries_for_habit(
        self, habit_id: int, start_date: date, end_date: date
    ) -> list[HabitEntry]:
        """Get entries for a habit within a date range."""
        ...

    def upsert_entry(self, entry: HabitEntry) -> HabitEntry:
        """Insert or update a habit entry."""
        ...

    def delete_entry(self, habit_id: int, occurred_on: date) -> None:
        """Delete a habit entry."""
        ...

    def get_current_streak(self, habit_id: int) -> int:
        """Calculate current streak for a habit."""
        ...

    def get_longest_streak(self, habit_id: int) -> int:
        """Calculate longest streak for a habit."""
        ...

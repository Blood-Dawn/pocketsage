"""Repository for managing Habit and HabitEntry persistence with streak tracking."""

from datetime import date, datetime, timedelta, timezone

from sqlmodel import Session, select

from pocketsage.models.habits import HabitEntry


class HabitRepository:
    # Provides CRUD operations for Habits and HabitEntries.
    # Includes logic to recalculate streaks when new entries are added.

    def __init__(self, session: Session):
        self.session = session

    # Habit Entry Creation + Streak Recalculation
    def create_entry(self, habit_id: int, occurred_on: date | None = None) -> HabitEntry:
        """
        Create a new HabitEntry for the given habit and recalculate its streak.

        Args:
            habit_id (int): The ID of the habit.
            occurred_on (date | None): Date the habit was completed (defaults to today).

        Returns:
            HabitEntry: The persisted habit entry instance.
        """
        if occurred_on is None:
            occurred_on = date.today()

        # Check if an entry already exists for that day
        existing_entry = self.session.exec(
            select(HabitEntry)
            .where(HabitEntry.habit_id == habit_id)
            .where(HabitEntry.occurred_on == occurred_on)
        ).first()

        if existing_entry:
            return existing_entry  # Prevents duplicate entries for the same day

        # Create new entry
        entry = HabitEntry(
            habit_id=habit_id,
            occurred_on=occurred_on,
            value=1,
        )
        self.session.add(entry)
        self.session.commit()

        # After persisting, recalculate streak
        self.recalculate_streak(habit_id)

        return entry

    # Streak Recalculation
    def recalculate_streak(self, habit_id: int) -> int:
        """
        Compute the current streak (consecutive days completed).

        Returns:
            int: Number of consecutive completion days ending today.
        """
        entries = self.session.exec(
            select(HabitEntry)
            .where(HabitEntry.habit_id == habit_id)
            .order_by(HabitEntry.occurred_on.desc())
        ).all()

        streak = 0
        today = date.today()

        for entry in entries:
            expected_day = today - timedelta(days=streak)
            if entry.occurred_on == expected_day:
                streak += 1
            else:
                break

        print(f"[{datetime.now(timezone.utc)}] Habit {habit_id} streak = {streak}")
        return streak

    # Helper Methods
    def get_habit_entries(self, habit_id: int):
        """Return all entries for a habit, newest first."""
        return self.session.exec(
            select(HabitEntry)
            .where(HabitEntry.habit_id == habit_id)
            .order_by(HabitEntry.occurred_on.desc())
        ).all()

    def delete_entry(self, habit_id: int, occurred_on: date):
        """Remove an entry and recalc streak."""
        entry = self.session.exec(
            select(HabitEntry)
            .where(HabitEntry.habit_id == habit_id)
            .where(HabitEntry.occurred_on == occurred_on)
        ).first()

        if not entry:
            return False

        self.session.delete(entry)
        self.session.commit()
        self.recalculate_streak(habit_id)
        return True

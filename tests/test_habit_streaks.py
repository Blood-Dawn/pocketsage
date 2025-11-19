"""Comprehensive tests for habit streak calculations.

These tests verify the logic for calculating current and longest streaks,
including edge cases like:
- Consecutive days
- Gaps in habit completion
- Streaks starting today vs in the past
- Empty habit data
- Timezone boundaries (if applicable)
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from src.pocketsage.infra.repositories.habit import SQLModelHabitRepository
from src.pocketsage.models.habit import Habit, HabitEntry


class TestCurrentStreak:
    """Tests for calculating current consecutive day streaks."""

    def test_no_entries_returns_zero_streak(self, session_factory, habit_factory):
        """Habit with no entries should have zero current streak."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        streak = repo.get_current_streak(habit.id)
        assert streak == 0

    def test_single_entry_today_returns_one(self, session_factory, habit_factory, db_session):
        """Single entry for today should return streak of 1."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        # Add entry for today
        today = date.today()
        entry = HabitEntry(habit_id=habit.id, occurred_on=today, value=1)
        db_session.add(entry)
        db_session.commit()

        streak = repo.get_current_streak(habit.id)
        assert streak == 1

    def test_consecutive_days_returns_correct_streak(self, session_factory, habit_factory, db_session):
        """Consecutive days should calculate streak correctly."""
        habit = habit_factory(name="Meditation")
        repo = SQLModelHabitRepository(session_factory)

        # Add 7 consecutive days ending today
        today = date.today()
        for i in range(7):
            day = today - timedelta(days=i)
            entry = HabitEntry(habit_id=habit.id, occurred_on=day, value=1)
            db_session.add(entry)
        db_session.commit()

        streak = repo.get_current_streak(habit.id)
        assert streak == 7

    def test_gap_breaks_streak(self, session_factory, habit_factory, db_session):
        """Gap in entries should break the current streak."""
        habit = habit_factory(name="Reading")
        repo = SQLModelHabitRepository(session_factory)

        today = date.today()

        # Add entries for today and yesterday
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=today, value=1))
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=today - timedelta(days=1), value=1))

        # Skip day before yesterday (gap)

        # Add older entries (before the gap)
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=today - timedelta(days=3), value=1))
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=today - timedelta(days=4), value=1))
        db_session.commit()

        # Current streak should only be 2 (today + yesterday)
        streak = repo.get_current_streak(habit.id)
        assert streak == 2

    def test_missing_today_returns_zero(self, session_factory, habit_factory, db_session):
        """If today's entry is missing, current streak should be 0."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        # Add entries for yesterday and before, but not today
        yesterday = date.today() - timedelta(days=1)
        for i in range(5):
            day = yesterday - timedelta(days=i)
            entry = HabitEntry(habit_id=habit.id, occurred_on=day, value=1)
            db_session.add(entry)
        db_session.commit()

        # Current streak should be 0 (no entry for today)
        streak = repo.get_current_streak(habit.id)
        assert streak == 0

    def test_zero_value_breaks_streak(self, session_factory, habit_factory, db_session):
        """Entry with value=0 should not count towards streak."""
        habit = habit_factory(name="Running")
        repo = SQLModelHabitRepository(session_factory)

        today = date.today()

        # Add entries, but middle one has value=0
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=today, value=1))
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=today - timedelta(days=1), value=0))  # Skipped
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=today - timedelta(days=2), value=1))
        db_session.commit()

        # Current streak should only be 1 (today), since yesterday was 0
        streak = repo.get_current_streak(habit.id)
        assert streak == 1


class TestLongestStreak:
    """Tests for calculating the longest historical streak."""

    def test_no_entries_returns_zero(self, session_factory, habit_factory):
        """Habit with no entries should have longest streak of 0."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        streak = repo.get_longest_streak(habit.id)
        assert streak == 0

    def test_single_entry_returns_one(self, session_factory, habit_factory, db_session):
        """Single entry should return longest streak of 1."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        entry = HabitEntry(habit_id=habit.id, occurred_on=date.today(), value=1)
        db_session.add(entry)
        db_session.commit()

        streak = repo.get_longest_streak(habit.id)
        assert streak == 1

    def test_consecutive_days_calculates_longest(self, session_factory, habit_factory, db_session):
        """Consecutive days should be counted as longest streak."""
        habit = habit_factory(name="Meditation")
        repo = SQLModelHabitRepository(session_factory)

        # Add 10 consecutive days
        start_date = date(2024, 1, 1)
        for i in range(10):
            day = start_date + timedelta(days=i)
            entry = HabitEntry(habit_id=habit.id, occurred_on=day, value=1)
            db_session.add(entry)
        db_session.commit()

        streak = repo.get_longest_streak(habit.id)
        assert streak == 10

    def test_multiple_streaks_returns_longest(self, session_factory, habit_factory, db_session):
        """Multiple streaks should return the longest one."""
        habit = habit_factory(name="Reading")
        repo = SQLModelHabitRepository(session_factory)

        # First streak: 3 days
        start1 = date(2024, 1, 1)
        for i in range(3):
            day = start1 + timedelta(days=i)
            db_session.add(HabitEntry(habit_id=habit.id, occurred_on=day, value=1))

        # Gap

        # Second streak: 7 days (longest)
        start2 = date(2024, 1, 10)
        for i in range(7):
            day = start2 + timedelta(days=i)
            db_session.add(HabitEntry(habit_id=habit.id, occurred_on=day, value=1))

        # Gap

        # Third streak: 4 days
        start3 = date(2024, 1, 20)
        for i in range(4):
            day = start3 + timedelta(days=i)
            db_session.add(HabitEntry(habit_id=habit.id, occurred_on=day, value=1))

        db_session.commit()

        # Longest streak should be 7
        streak = repo.get_longest_streak(habit.id)
        assert streak == 7

    def test_current_streak_can_be_longest(self, session_factory, habit_factory, db_session):
        """Current active streak can be the longest streak."""
        habit = habit_factory(name="Yoga")
        repo = SQLModelHabitRepository(session_factory)

        # Old short streak
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=date(2024, 1, 1), value=1))
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=date(2024, 1, 2), value=1))

        # Gap

        # Current long streak (14 days ending today)
        today = date.today()
        for i in range(14):
            day = today - timedelta(days=i)
            db_session.add(HabitEntry(habit_id=habit.id, occurred_on=day, value=1))

        db_session.commit()

        # Longest should be the current streak (14)
        longest = repo.get_longest_streak(habit.id)
        current = repo.get_current_streak(habit.id)

        assert longest == 14
        assert current == 14
        assert longest == current

    def test_zero_value_entries_ignored(self, session_factory, habit_factory, db_session):
        """Entries with value=0 should not be counted in longest streak."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        start_date = date(2024, 1, 1)

        # Add 5 days, but day 3 has value=0
        for i in range(5):
            day = start_date + timedelta(days=i)
            value = 0 if i == 2 else 1  # Skip day 3
            db_session.add(HabitEntry(habit_id=habit.id, occurred_on=day, value=value))

        db_session.commit()

        # Longest streak should be 2 (days 1-2 before the skip)
        # or 2 (days 4-5 after the skip)
        streak = repo.get_longest_streak(habit.id)
        assert streak == 2

    def test_non_consecutive_dates_creates_multiple_streaks(self, session_factory, habit_factory, db_session):
        """Non-consecutive dates should create separate streaks."""
        habit = habit_factory(name="Study")
        repo = SQLModelHabitRepository(session_factory)

        # Streak 1: Jan 1-3 (3 days)
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=date(2024, 1, 1), value=1))
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=date(2024, 1, 2), value=1))
        db_session.add(HabitEntry(habit_id=habit.id, occurred_on=date(2024, 1, 3), value=1))

        # Gap: Jan 4-9 missing

        # Streak 2: Jan 10-15 (6 days) - LONGEST
        for i in range(6):
            day = date(2024, 1, 10) + timedelta(days=i)
            db_session.add(HabitEntry(habit_id=habit.id, occurred_on=day, value=1))

        # Gap: Jan 16-19 missing

        # Streak 3: Jan 20-22 (3 days)
        for i in range(3):
            day = date(2024, 1, 20) + timedelta(days=i)
            db_session.add(HabitEntry(habit_id=habit.id, occurred_on=day, value=1))

        db_session.commit()

        # Longest should be 6 days
        streak = repo.get_longest_streak(habit.id)
        assert streak == 6


class TestHabitEntryUpsert:
    """Tests for upserting habit entries (insert or update)."""

    def test_upsert_creates_new_entry(self, session_factory, habit_factory):
        """Upsert should create new entry if none exists."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        today = date.today()
        entry = HabitEntry(habit_id=habit.id, occurred_on=today, value=1)

        upserted = repo.upsert_entry(entry)

        assert upserted.habit_id == habit.id
        assert upserted.occurred_on == today
        assert upserted.value == 1

    def test_upsert_updates_existing_entry(self, session_factory, habit_factory, db_session):
        """Upsert should update existing entry for same date."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        today = date.today()

        # Create initial entry
        entry1 = HabitEntry(habit_id=habit.id, occurred_on=today, value=1)
        db_session.add(entry1)
        db_session.commit()

        # Upsert with different value
        entry2 = HabitEntry(habit_id=habit.id, occurred_on=today, value=3)
        upserted = repo.upsert_entry(entry2)

        # Should have updated, not created new
        assert upserted.value == 3

        # Verify only one entry exists
        entries = repo.get_entries_for_habit(habit.id, today, today)
        assert len(entries) == 1
        assert entries[0].value == 3

    def test_upsert_different_dates_creates_separate_entries(self, session_factory, habit_factory):
        """Upsert for different dates should create separate entries."""
        habit = habit_factory(name="Reading")
        repo = SQLModelHabitRepository(session_factory)

        today = date.today()
        yesterday = today - timedelta(days=1)

        # Upsert for today
        entry1 = HabitEntry(habit_id=habit.id, occurred_on=today, value=1)
        repo.upsert_entry(entry1)

        # Upsert for yesterday
        entry2 = HabitEntry(habit_id=habit.id, occurred_on=yesterday, value=1)
        repo.upsert_entry(entry2)

        # Should have 2 separate entries
        entries = repo.get_entries_for_habit(habit.id, yesterday, today)
        assert len(entries) == 2


class TestGetEntriesForHabit:
    """Tests for retrieving habit entries within a date range."""

    def test_empty_date_range_returns_empty_list(self, session_factory, habit_factory):
        """Query for habit with no entries should return empty list."""
        habit = habit_factory(name="Exercise")
        repo = SQLModelHabitRepository(session_factory)

        today = date.today()
        entries = repo.get_entries_for_habit(habit.id, today, today)

        assert entries == []

    def test_get_entries_in_range(self, session_factory, habit_factory, db_session):
        """Should return only entries within specified date range."""
        habit = habit_factory(name="Meditation")
        repo = SQLModelHabitRepository(session_factory)

        # Add entries for multiple days
        base_date = date(2024, 1, 1)
        for i in range(10):
            day = base_date + timedelta(days=i)
            entry = HabitEntry(habit_id=habit.id, occurred_on=day, value=1)
            db_session.add(entry)
        db_session.commit()

        # Query for middle 5 days
        start = base_date + timedelta(days=2)  # Jan 3
        end = base_date + timedelta(days=6)  # Jan 7

        entries = repo.get_entries_for_habit(habit.id, start, end)

        # Should return 5 entries (Jan 3, 4, 5, 6, 7)
        assert len(entries) == 5
        assert entries[0].occurred_on == start
        assert entries[-1].occurred_on == end

    def test_entries_ordered_by_date(self, session_factory, habit_factory, db_session):
        """Entries should be returned in ascending date order."""
        habit = habit_factory(name="Reading")
        repo = SQLModelHabitRepository(session_factory)

        # Add entries in random order
        dates = [
            date(2024, 1, 5),
            date(2024, 1, 1),
            date(2024, 1, 3),
            date(2024, 1, 7),
            date(2024, 1, 2),
        ]

        for d in dates:
            entry = HabitEntry(habit_id=habit.id, occurred_on=d, value=1)
            db_session.add(entry)
        db_session.commit()

        # Query all
        entries = repo.get_entries_for_habit(
            habit.id,
            date(2024, 1, 1),
            date(2024, 1, 31),
        )

        # Should be ordered by date
        assert len(entries) == 5
        for i in range(len(entries) - 1):
            assert entries[i].occurred_on < entries[i + 1].occurred_on

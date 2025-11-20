"""Habits tracking data structures."""

from __future__ import annotations

from datetime import date
from typing import ClassVar, Optional

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel


class Habit(SQLModel, table=True):
    """A user-defined habit the app tracks daily."""

    __tablename__: ClassVar[str] = "habit"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=80, index=True)
    description: str = Field(default="", max_length=255)
    cadence: str = Field(default="daily", max_length=32)
    is_active: bool = Field(default=True, nullable=False)

    entries: list["HabitEntry"] = Relationship(
        back_populates="habit",
        sa_relationship=relationship("HabitEntry", back_populates="habit"),
    )

    # TODO(@habits-squad): add owner foreign key when multi-user support arrives.


class HabitEntry(SQLModel, table=True):
    """Individual completion record for a habit on a calendar day."""

    __tablename__: ClassVar[str] = "habit_entry"

    habit_id: int = Field(foreign_key="habit.id", primary_key=True)
    occurred_on: date = Field(primary_key=True, index=True)
    value: int = Field(default=1, nullable=False)

    habit: "Habit" = Relationship(
        back_populates="entries",
        sa_relationship=relationship("Habit", back_populates="entries"),
    )

    # TODO(@analytics): enforce timezone-aware capture for cross-region tracking.

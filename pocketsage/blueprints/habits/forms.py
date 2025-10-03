"""Habit form stubs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class HabitForm:
    """Placeholder for habit creation/edit form."""

    name: str = ""
    description: str = ""
    cadence: str = "daily"

    def validate(self) -> bool:
        """Validate habit inputs."""

        # TODO(@habits-squad): implement validation + error messaging.
        raise NotImplementedError

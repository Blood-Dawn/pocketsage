"""Habit form definitions."""

from __future__ import annotations

from datetime import time
from enum import Enum
from typing import Iterable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class HabitCadence(str, Enum):
    """Supported cadence options for habits."""

    DAILY = "daily"
    WEEKLY = "weekly"
    CUSTOM = "custom"


class HabitForm(BaseModel):
    """Form model for creating or editing a habit."""

    model_config = ConfigDict(validate_default=False, str_strip_whitespace=True)

    name: str = Field(default="", description="Short label for the habit", max_length=100)
    description: str = Field(default="", description="Optional details about the habit", max_length=400)
    cadence: HabitCadence = Field(default=HabitCadence.DAILY, description="Habit frequency")
    custom_interval_days: int | None = Field(
        default=None,
        ge=1,
        le=365,
        description="Number of days between habit completions when using custom cadence",
    )
    reminders_enabled: bool = Field(default=True, description="Toggle habit reminders")
    reminder_time: time | None = Field(default=time(hour=9), description="Preferred reminder time")
    tags: list[str] = Field(default_factory=list, description="Optional list of habit tags")

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        """Ensure the habit name is present when validating submissions."""

        if not value or not value.strip():
            raise ValueError("Please provide a habit name.")
        return value

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, value: str | Iterable[str]) -> list[str] | Iterable[str]:
        """Convert comma-separated tag strings into a list."""

        if isinstance(value, str):
            return [tag for tag in (part.strip() for part in value.split(",")) if tag]
        return value

    @model_validator(mode="after")
    def ensure_custom_interval(self) -> "HabitForm":
        """Require an interval when custom cadence is selected."""

        if self.cadence is HabitCadence.CUSTOM and not self.custom_interval_days:
            raise ValueError("Set the number of days for a custom cadence.")
        return self

    def validation_errors(self) -> dict[str, list[str]]:
        """Return validation errors for the current payload."""

        try:
            HabitForm.model_validate(self.model_dump())
        except ValidationError as exc:  # pragma: no cover - passthrough helper
            structured: dict[str, list[str]] = {}
            for error in exc.errors(include_url=False):
                loc = error.get("loc", ())
                key = loc[0] if loc else "__root__"
                structured.setdefault(key, []).append(error.get("msg", "Invalid value"))
            return structured
        return {}


__all__ = ["HabitCadence", "HabitForm"]

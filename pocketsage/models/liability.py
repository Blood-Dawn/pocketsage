"""Debt and liability entities."""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlmodel import Field, SQLModel


class Liability(SQLModel, table=True):
    """Installment or revolving debt tracked in PocketSage."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=80, index=True)
    balance: float = Field(nullable=False)
    apr: float = Field(default=0.0, nullable=False)
    minimum_payment: float = Field(default=0.0, nullable=False)
    due_day: int = Field(default=1, ge=1, le=28)
    opened_on: Optional[date] = Field(default=None)
    payoff_strategy: str = Field(default="snowball", max_length=32)

    # TODO(@debts-squad): link to transactions + payment history table.

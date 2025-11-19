"""Debt and liability entities."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .transaction import Transaction


class Liability(SQLModel, table=True):
    """Installment or revolving debt tracked in PocketSage."""

    __tablename__ = "liability"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=80, index=True)
    balance: float = Field(nullable=False)
    apr: float = Field(default=0.0, nullable=False)
    minimum_payment: float = Field(default=0.0, nullable=False)
    due_day: int = Field(default=1, ge=1, le=28)
    opened_on: Optional[date] = Field(default=None)
    payoff_strategy: str = Field(default="snowball", max_length=32)

    # Relationships for linking to other tables
    transactions: list["Transaction"] = Relationship(back_populates="liability")
    # For a dedicated payment history table, you would define another relationship here.
    # For example: payment_history: list[PaymentHistory] = Relationship(back_populates="liability")

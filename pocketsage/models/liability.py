"""Debt and liability entities."""

from __future__ import annotations

from datetime import date
from typing import Optional, List

from sqlmodel import Field, SQLModel, Relationship


class Transaction(SQLModel, table=True):
    """Placeholder for the Transaction model to define a relationship."""
    id: Optional[int] = Field(default=None, primary_key=True)
    # Other transaction fields would go here, such as date, amount, etc.
    # For now, we just need the relationship field.
    liability_id: Optional[int] = Field(default=None, foreign_key="liability.id")


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
    
    # Relationships for linking to other tables
    transactions: List[Transaction] = Relationship(back_populates="liability")
    # For a dedicated payment history table, you would define another relationship here.
    # For example: payment_history: List[PaymentHistory] = Relationship(back_populates="liability")

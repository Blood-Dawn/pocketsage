"""Debt and liability entities."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, ClassVar, Optional

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .transaction import Transaction
    from .user import User


class Liability(SQLModel, table=True):
    """Installment or revolving debt tracked in PocketSage."""

    __tablename__: ClassVar[str] = "liability"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    name: str = Field(nullable=False, max_length=80, index=True)
    balance: float = Field(nullable=False)
    apr: float = Field(default=0.0, nullable=False)
    minimum_payment: float = Field(default=0.0, nullable=False)
    due_day: int = Field(default=1, ge=1, le=28)
    opened_on: Optional[date] = Field(default=None)
    payoff_strategy: str = Field(default="snowball", max_length=32)

    # Relationships for linking to other tables
    transactions: list["Transaction"] = Relationship(
        back_populates="liability",
        sa_relationship=relationship("Transaction", back_populates="liability"),
    )
    user: "User" = Relationship(sa_relationship=relationship("User", back_populates="liabilities"))
    # For a dedicated payment history table, you would define another relationship here.
    # For example: payment_history: list[PaymentHistory] = Relationship(back_populates="liability")

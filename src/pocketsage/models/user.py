"""User model supporting authentication and roles."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import ClassVar, Optional

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel


class User(SQLModel, table=True):
    """Application user with role and credentials."""

    __tablename__: ClassVar[str] = "user"

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(nullable=False, unique=True, index=True, max_length=64)
    password_hash: str = Field(nullable=False, max_length=255)
    role: str = Field(default="user", nullable=False, max_length=16, index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    last_login: Optional[datetime] = Field(default=None)

    accounts = Relationship(
        back_populates="user",
        sa_relationship=relationship("Account", back_populates="user"),
    )
    transactions = Relationship(
        back_populates="user",
        sa_relationship=relationship("Transaction", back_populates="user"),
    )
    categories = Relationship(
        back_populates="user",
        sa_relationship=relationship("Category", back_populates="user"),
    )
    habits = Relationship(
        back_populates="user",
        sa_relationship=relationship("Habit", back_populates="user"),
    )
    liabilities = Relationship(
        back_populates="user",
        sa_relationship=relationship("Liability", back_populates="user"),
    )
    holdings = Relationship(
        back_populates="user",
        sa_relationship=relationship("Holding", back_populates="user"),
    )
    budgets = Relationship(
        back_populates="user",
        sa_relationship=relationship("Budget", back_populates="user"),
    )

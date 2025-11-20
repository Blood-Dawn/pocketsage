"""Budgeting tables."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, ClassVar, Optional

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .user import User


class Budget(SQLModel, table=True):
    """A time-boxed budget envelope group."""

    __tablename__: ClassVar[str] = "budget"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    period_start: date = Field(index=True, nullable=False)
    period_end: date = Field(index=True, nullable=False)
    label: str = Field(default="", max_length=64)

    lines: list["BudgetLine"] = Relationship(
        back_populates="budget",
        sa_relationship=relationship("BudgetLine", back_populates="budget"),
    )

    user: "User" = Relationship(sa_relationship=relationship("User", back_populates="budgets"))

    # TODO(@budgeting): enforce non-overlapping windows per user.


class BudgetLine(SQLModel, table=True):
    """Specific allocation to a category within a budget."""

    __tablename__: ClassVar[str] = "budget_line"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    budget_id: int = Field(foreign_key="budget.id", nullable=False)
    category_id: int = Field(foreign_key="category.id", nullable=False)
    planned_amount: float = Field(nullable=False)
    rollover_enabled: bool = Field(default=False, nullable=False)

    budget: "Budget" = Relationship(
        back_populates="lines",
        sa_relationship=relationship("Budget", back_populates="lines"),
    )
    user: "User" = Relationship(sa_relationship=relationship("User"))

    # TODO(@budgeting): track actual spend + available with materialized views.

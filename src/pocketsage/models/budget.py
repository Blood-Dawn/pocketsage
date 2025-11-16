"""Budgeting tables."""

from datetime import date
from typing import List, Optional

from sqlmodel import Field, Relationship, SQLModel


class Budget(SQLModel, table=True):
    """A time-boxed budget envelope group."""

    id: Optional[int] = Field(default=None, primary_key=True)
    period_start: date = Field(index=True, nullable=False)
    period_end: date = Field(index=True, nullable=False)
    label: str = Field(default="", max_length=64)

    lines: List["BudgetLine"] = Relationship(back_populates="budget")

    # TODO(@budgeting): enforce non-overlapping windows per user.


class BudgetLine(SQLModel, table=True):
    """Specific allocation to a category within a budget."""

    id: Optional[int] = Field(default=None, primary_key=True)
    budget_id: int = Field(foreign_key="budget.id", nullable=False)
    category_id: int = Field(foreign_key="category.id", nullable=False)
    planned_amount: float = Field(nullable=False)
    rollover_enabled: bool = Field(default=False, nullable=False)

    budget: "Budget" = Relationship(back_populates="lines")

    # TODO(@budgeting): track actual spend + available with materialized views.

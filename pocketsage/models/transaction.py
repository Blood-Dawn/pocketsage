"""SQLModel definitions for ledger transactions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover - import guard for circular dependency
    from .category import Category


class Transaction(SQLModel, table=True):
    """A single ledger transaction imported or hand-entered."""

    id: Optional[int] = Field(default=None, primary_key=True)
    occurred_at: datetime = Field(nullable=False, index=True)
    amount: float = Field(nullable=False, description="Positive for inflow, negative for outflow")
    memo: str = Field(default="", max_length=255)
    external_id: Optional[str] = Field(default=None, index=True, max_length=128)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")

    category: Optional["Category"] = Relationship(back_populates="transactions")

    # TODO(@data-team): enforce account linkage + currency once multi-account support lands.


class TransactionTagLink(SQLModel, table=True):
    """Association table enabling many-to-many tagging."""

    transaction_id: int = Field(foreign_key="transaction.id", primary_key=True)
    tag_id: int = Field(foreign_key="category.id", primary_key=True)
    # TODO(@data-team): replace tag_id FK with dedicated Tag table once taxonomy defined.

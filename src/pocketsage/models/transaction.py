"""SQLModel definitions for ledger transactions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover - import guard for circular dependency
    from .account import Account
    from .category import Category
    from .liability import Liability


class Transaction(SQLModel, table=True):
    """A single ledger transaction imported or hand-entered."""

    __tablename__ = "transaction"

    id: Optional[int] = Field(default=None, primary_key=True)
    occurred_at: datetime = Field(nullable=False, index=True)
    amount: float = Field(nullable=False, description="Positive for inflow, negative for outflow")
    memo: str = Field(default="", max_length=255)
    external_id: Optional[str] = Field(default=None, index=True, max_length=128)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")

    category: Optional["Category"] = Relationship(back_populates="transactions")

    # Link transactions to an account and record the currency used for the amount.
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")
    account: Optional["Account"] = Relationship(back_populates="transactions")
    currency: str = Field(default="USD", max_length=3, description="ISO-4217 currency code")

    # Link to liability for debt-related transactions
    liability_id: Optional[int] = Field(default=None, foreign_key="liability.id")
    liability: Optional["Liability"] = Relationship(back_populates="transactions")

    # TODO(@data-team): enforce account linkage + currency once multi-account support lands.


class TransactionTagLink(SQLModel, table=True):
    """Association table enabling many-to-many tagging."""

    __tablename__ = "transaction_tag_link"

    transaction_id: int = Field(foreign_key="transaction.id", primary_key=True)
    tag_id: int = Field(foreign_key="category.id", primary_key=True)
    # TODO(@data-team): replace tag_id FK with dedicated Tag table once taxonomy defined.

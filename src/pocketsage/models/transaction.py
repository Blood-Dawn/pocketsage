"""SQLModel definitions for ledger transactions."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Optional

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover - import guard for circular dependency
    from .account import Account
    from .category import Category
    from .liability import Liability
    from .user import User


class Transaction(SQLModel, table=True):
    """A single ledger transaction imported or hand-entered."""

    __tablename__: ClassVar[str] = "transaction"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    occurred_at: datetime = Field(nullable=False, index=True)
    amount: float = Field(nullable=False, description="Positive for inflow, negative for outflow")
    memo: str = Field(default="", max_length=255)
    external_id: Optional[str] = Field(default=None, index=True, max_length=128)
    category_id: Optional[int] = Field(default=None, foreign_key="category.id")

    category: "Category | None" = Relationship(
        back_populates="transactions",
        sa_relationship=relationship("Category", back_populates="transactions"),
    )

    # Link transactions to an account and record the currency used for the amount.
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")
    account: "Account | None" = Relationship(
        back_populates="transactions",
        sa_relationship=relationship("Account", back_populates="transactions"),
    )
    currency: str = Field(default="USD", max_length=3, description="ISO-4217 currency code")

    # Link to liability for debt-related transactions
    liability_id: Optional[int] = Field(default=None, foreign_key="liability.id")
    liability: "Liability | None" = Relationship(
        back_populates="transactions",
        sa_relationship=relationship("Liability", back_populates="transactions"),
    )
    user: "User" = Relationship(sa_relationship=relationship("User", back_populates="transactions"))

    # TODO(@data-team): enforce account linkage + currency once multi-account support lands.


class TransactionTagLink(SQLModel, table=True):
    """Association table enabling many-to-many tagging."""

    __tablename__: ClassVar[str] = "transaction_tag_link"

    transaction_id: int = Field(foreign_key="transaction.id", primary_key=True)
    tag_id: int = Field(foreign_key="category.id", primary_key=True)
    # TODO(@data-team): replace tag_id FK with dedicated Tag table once taxonomy defined.

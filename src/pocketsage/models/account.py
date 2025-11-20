"""Account model for transaction linkage."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Optional

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .portfolio import Holding
    from .transaction import Transaction


class Account(SQLModel, table=True):
    __tablename__: ClassVar[str] = "account"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=128)
    currency: str = Field(default="USD", max_length=3)

    transactions: list["Transaction"] = Relationship(
        back_populates="account",
        sa_relationship=relationship("Transaction", back_populates="account"),
    )
    holdings: list["Holding"] = Relationship(
        back_populates="account",
        sa_relationship=relationship("Holding", back_populates="account"),
    )

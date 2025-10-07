"""Account model for transaction linkage."""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .portfolio import Holding
    from .transaction import Transaction


class Account(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(nullable=False, max_length=128)
    currency: str = Field(default="USD", max_length=3)

    transactions: List["Transaction"] = Relationship(back_populates="account")
    holdings: List["Holding"] = Relationship(back_populates="account")

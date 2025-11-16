"""Portfolio models."""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .account import Account


class Holding(SQLModel, table=True):
    """Represents a portfolio holding snapshot."""

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, nullable=False, max_length=32)
    quantity: float = Field(nullable=False, default=0.0)
    avg_price: float = Field(nullable=False, default=0.0)
    acquired_at: Optional[datetime] = Field(default=None)
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")
    currency: str = Field(default="USD", max_length=3)

    account: Optional["Account"] = Relationship(back_populates="holdings")

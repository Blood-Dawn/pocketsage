"""Portfolio models."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, ClassVar, Optional

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .account import Account


class Holding(SQLModel, table=True):
    """Represents a portfolio holding snapshot."""

    __tablename__: ClassVar[str] = "holding"

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, nullable=False, max_length=32)
    quantity: float = Field(nullable=False, default=0.0)
    avg_price: float = Field(nullable=False, default=0.0)
    acquired_at: Optional[datetime] = Field(default=None)
    account_id: Optional[int] = Field(default=None, foreign_key="account.id")
    currency: str = Field(default="USD", max_length=3)

    account: "Account" = Relationship(
        back_populates="holdings",
        sa_relationship=relationship("Account", back_populates="holdings"),
    )

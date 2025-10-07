"""Portfolio models."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Holding(SQLModel, table=True):
    """Represents a portfolio holding snapshot."""

    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True, nullable=False, max_length=32)
    quantity: float = Field(nullable=False, default=0.0)
    avg_price: float = Field(nullable=False, default=0.0)
    acquired_at: Optional[datetime] = Field(default=None)

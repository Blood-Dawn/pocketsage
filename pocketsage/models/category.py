"""Ledger category definitions."""

from typing import TYPE_CHECKING, List, Optional

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .transaction import Transaction


class Category(SQLModel, table=True):
    """Transaction category used for budgeting and reporting."""

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True, nullable=False, max_length=64)
    slug: str = Field(index=True, nullable=False, max_length=64, unique=True)
    category_type: str = Field(default="expense", nullable=False, max_length=32)
    color: Optional[str] = Field(default=None, max_length=7)

    transactions: List["Transaction"] = Relationship(back_populates="category")

    # TODO(@ux-team): enforce palette uniqueness + icon set once design assets land.

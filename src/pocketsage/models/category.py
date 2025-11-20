"""Ledger category definitions."""

from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar, Optional

from sqlalchemy.orm import relationship
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:  # pragma: no cover
    from .transaction import Transaction
    from .user import User


class Category(SQLModel, table=True):
    """Transaction category used for budgeting and reporting."""

    __tablename__: ClassVar[str] = "category"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    name: str = Field(index=True, nullable=False, max_length=64)
    slug: str = Field(index=True, nullable=False, max_length=64)
    category_type: str = Field(default="expense", nullable=False, max_length=32)
    color: Optional[str] = Field(default=None, max_length=7)

    transactions: list["Transaction"] = Relationship(
        back_populates="category",
        sa_relationship=relationship("Transaction", back_populates="category"),
    )

    user: "User" = Relationship(sa_relationship=relationship("User", back_populates="categories"))

    # TODO(@ux-team): enforce palette uniqueness + icon set once design assets land.

"""Application-level settings stored in the database."""

from __future__ import annotations

from typing import ClassVar, Optional

from sqlmodel import Field, SQLModel


class AppSetting(SQLModel, table=True):
    """Key-value storage for runtime configurable options."""

    __tablename__: ClassVar[str] = "app_setting"

    key: str = Field(primary_key=True, max_length=64)
    value: str = Field(nullable=False, max_length=255)
    description: Optional[str] = Field(default=None, max_length=255)

    # TODO(@ops-team): add updated_at timestamp + audit trail for setting changes.

"""Settings repository for app-level key/value pairs."""

from __future__ import annotations

from typing import Callable, Optional

from sqlmodel import Session, select

from ...models.settings import AppSetting


class SQLModelSettingsRepository:
    """SQLModel-based settings repository."""

    def __init__(self, session_factory: Callable[[], Session]):
        self.session_factory = session_factory

    def get(self, key: str) -> Optional[AppSetting]:
        with self.session_factory() as session:
            return session.exec(select(AppSetting).where(AppSetting.key == key)).first()

    def set(self, key: str, value: str, description: str | None = None) -> AppSetting:
        with self.session_factory() as session:
            setting = session.exec(select(AppSetting).where(AppSetting.key == key)).first()
            if setting:
                setting.value = value
                setting.description = description
            else:
                setting = AppSetting(key=key, value=value, description=description)
                session.add(setting)
            session.commit()
            session.refresh(setting)
            return setting

    def delete(self, key: str) -> None:
        with self.session_factory() as session:
            setting = session.exec(select(AppSetting).where(AppSetting.key == key)).first()
            if setting:
                session.delete(setting)
                session.commit()


__all__ = ["SQLModelSettingsRepository"]

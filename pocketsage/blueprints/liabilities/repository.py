"""Liabilities repository contract and SQLModel implementation."""

from __future__ import annotations

from typing import Iterable, Protocol

from sqlmodel import Session, select

from ...models.liability import Liability
from ...services.liabilities import PaymentProjection, flatten_schedules


class LiabilitiesRepository(Protocol):
    """Persistence contract for liabilities."""

    def list_liabilities(self) -> Iterable[Liability]:  # pragma: no cover - interface
        ...

    def create_liability(self, *, payload: dict) -> Liability:  # pragma: no cover - interface
        ...

    def schedule_payoff(self, *, liability_id: int) -> None:  # pragma: no cover - interface
        ...

    def build_schedules(
        self, *, liabilities: Iterable[Liability], horizon_months: int = 12
    ) -> dict[int, list[PaymentProjection]]:  # pragma: no cover - interface
        ...


class SqlModelLiabilitiesRepository(LiabilitiesRepository):
    """SQLModel-backed implementation for liability operations."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def list_liabilities(self) -> Iterable[Liability]:
        statement = select(Liability).order_by(Liability.due_day, Liability.name)
        return list(self._session.exec(statement))

    def create_liability(self, *, payload: dict) -> Liability:
        liability = Liability(**payload)
        self._session.add(liability)
        self._session.flush()
        return liability

    def schedule_payoff(self, *, liability_id: int) -> None:  # pragma: no cover - async stub
        raise NotImplementedError("Payoff scheduling requires background job integration")

    def build_schedules(
        self, *, liabilities: Iterable[Liability], horizon_months: int = 12
    ) -> dict[int, list[PaymentProjection]]:
        return flatten_schedules(liabilities=liabilities, months=horizon_months)


__all__ = ["LiabilitiesRepository", "SqlModelLiabilitiesRepository"]

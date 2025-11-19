"""SQLModel implementation of Liability repository."""

from __future__ import annotations

from typing import Callable, Optional

from sqlmodel import Session, select

from ...models.liability import Liability


class SQLModelLiabilityRepository:
    """SQLModel-based liability repository implementation."""

    def __init__(self, session_factory: Callable[[], Session]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    def get_by_id(self, liability_id: int) -> Optional[Liability]:
        """Retrieve a liability by ID."""
        with self.session_factory() as session:
            return session.get(Liability, liability_id)

    def get_by_name(self, name: str) -> Optional[Liability]:
        """Retrieve a liability by name."""
        with self.session_factory() as session:
            statement = select(Liability).where(Liability.name == name)
            return session.exec(statement).first()

    def list_all(self) -> list[Liability]:
        """List all liabilities."""
        with self.session_factory() as session:
            statement = select(Liability).order_by(Liability.name)  # type: ignore
            return list(session.exec(statement).all())

    def list_active(self) -> list[Liability]:
        """List liabilities with non-zero balances."""
        with self.session_factory() as session:
            statement = (
                select(Liability)
                .where(Liability.balance > 0)
                .order_by(Liability.name)  # type: ignore
            )
            return list(session.exec(statement).all())

    def create(self, liability: Liability) -> Liability:
        """Create a new liability."""
        with self.session_factory() as session:
            session.add(liability)
            session.commit()
            session.refresh(liability)
            return liability

    def update(self, liability: Liability) -> Liability:
        """Update an existing liability."""
        with self.session_factory() as session:
            session.add(liability)
            session.commit()
            session.refresh(liability)
            return liability

    def delete(self, liability_id: int) -> None:
        """Delete a liability by ID."""
        with self.session_factory() as session:
            if liability := session.get(Liability, liability_id):
                session.delete(liability)
                session.commit()

    def get_total_debt(self) -> float:
        """Calculate total outstanding debt."""
        with self.session_factory() as session:
            liabilities = session.exec(select(Liability)).all()
            return sum(liability.balance for liability in liabilities)

    def get_weighted_apr(self) -> float:
        """Calculate weighted average APR across all liabilities."""
        with self.session_factory() as session:
            liabilities = list(session.exec(select(Liability)).all())

            if not liabilities:
                return 0.0

            total_balance = sum(liability.balance for liability in liabilities)
            if total_balance == 0:
                return 0.0

            weighted_sum = sum(liability.balance * liability.apr for liability in liabilities)
            return weighted_sum / total_balance

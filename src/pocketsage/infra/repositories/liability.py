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

    def get_by_id(self, liability_id: int, *, user_id: int) -> Optional[Liability]:
        """Retrieve a liability by ID."""
        with self.session_factory() as session:
            return session.exec(
                select(Liability).where(Liability.id == liability_id, Liability.user_id == user_id)
            ).first()

    def get_by_name(self, name: str, *, user_id: int) -> Optional[Liability]:
        """Retrieve a liability by name."""
        with self.session_factory() as session:
            statement = select(Liability).where(
                Liability.name == name, Liability.user_id == user_id
            )
            return session.exec(statement).first()

    def list_all(self, *, user_id: int) -> list[Liability]:
        """List all liabilities."""
        with self.session_factory() as session:
            statement = (
                select(Liability)
                .where(Liability.user_id == user_id)
                .order_by(Liability.name)  # type: ignore
            )
            return list(session.exec(statement).all())

    def list_active(self, *, user_id: int) -> list[Liability]:
        """List liabilities with non-zero balances."""
        with self.session_factory() as session:
            statement = (
                select(Liability)
                .where(Liability.user_id == user_id)
                .where(Liability.balance > 0)
                .order_by(Liability.name)  # type: ignore
            )
            return list(session.exec(statement).all())

    def create(self, liability: Liability, *, user_id: int) -> Liability:
        """Create a new liability."""
        with self.session_factory() as session:
            liability.user_id = user_id
            session.add(liability)
            session.commit()
            session.refresh(liability)
            return liability

    def update(self, liability: Liability, *, user_id: int) -> Liability:
        """Update an existing liability."""
        with self.session_factory() as session:
            liability.user_id = user_id
            session.add(liability)
            session.commit()
            session.refresh(liability)
            return liability

    def delete(self, liability_id: int, *, user_id: int) -> None:
        """Delete a liability by ID."""
        with self.session_factory() as session:
            liability = session.exec(
                select(Liability).where(Liability.id == liability_id, Liability.user_id == user_id)
            ).first()
            if liability:
                session.delete(liability)
                session.commit()

    def get_total_debt(self, *, user_id: int) -> float:
        """Calculate total outstanding debt."""
        with self.session_factory() as session:
            liabilities = session.exec(select(Liability).where(Liability.user_id == user_id)).all()
            return sum(liability.balance for liability in liabilities)

    def get_weighted_apr(self, *, user_id: int) -> float:
        """Calculate weighted average APR across all liabilities."""
        with self.session_factory() as session:
            liabilities = list(
                session.exec(select(Liability).where(Liability.user_id == user_id)).all()
            )

            if not liabilities:
                return 0.0

            total_balance = sum(liability.balance for liability in liabilities)
            if total_balance == 0:
                return 0.0

            weighted_sum = sum(liability.balance * liability.apr for liability in liabilities)
            return weighted_sum / total_balance

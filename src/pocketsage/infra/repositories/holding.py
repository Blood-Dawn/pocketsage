"""SQLModel implementation of Holding repository."""

from __future__ import annotations

from typing import Callable, Optional

from sqlmodel import Session, select

from ...models.portfolio import Holding


class SQLModelHoldingRepository:
    """SQLModel-based holding repository implementation."""

    def __init__(self, session_factory: Callable[[], Session]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    def get_by_id(self, holding_id: int, *, user_id: int) -> Optional[Holding]:
        """Retrieve a holding by ID."""
        with self.session_factory() as session:
            return session.exec(
                select(Holding).where(Holding.id == holding_id, Holding.user_id == user_id)
            ).first()

    def get_by_symbol(
        self, symbol: str, *, user_id: int, account_id: Optional[int] = None
    ) -> Optional[Holding]:
        """Retrieve a holding by symbol and optionally account."""
        with self.session_factory() as session:
            statement = select(Holding).where(Holding.symbol == symbol, Holding.user_id == user_id)

            if account_id is not None:
                statement = statement.where(Holding.account_id == account_id)

            return session.exec(statement).first()

    def list_all(self, *, user_id: int) -> list[Holding]:
        """List all holdings."""
        with self.session_factory() as session:
            statement = (
                select(Holding)
                .where(Holding.user_id == user_id)
                .order_by(Holding.symbol)  # type: ignore
            )
            return list(session.exec(statement).all())

    def list_by_account(self, account_id: int, *, user_id: int) -> list[Holding]:
        """List holdings for a specific account."""
        with self.session_factory() as session:
            statement = (
                select(Holding)
                .where(Holding.user_id == user_id)
                .where(Holding.account_id == account_id)
                .order_by(Holding.symbol)  # type: ignore
            )
            return list(session.exec(statement).all())

    def create(self, holding: Holding, *, user_id: int) -> Holding:
        """Create a new holding."""
        with self.session_factory() as session:
            holding.user_id = user_id
            session.add(holding)
            session.commit()
            session.refresh(holding)
            return holding

    def update(self, holding: Holding, *, user_id: int) -> Holding:
        """Update an existing holding."""
        with self.session_factory() as session:
            holding.user_id = user_id
            session.add(holding)
            session.commit()
            session.refresh(holding)
            return holding

    def delete(self, holding_id: int, *, user_id: int) -> None:
        """Delete a holding by ID."""
        with self.session_factory() as session:
            holding = session.exec(
                select(Holding).where(Holding.id == holding_id, Holding.user_id == user_id)
            ).first()
            if holding:
                session.delete(holding)
                session.commit()

    def get_total_cost_basis(self, *, user_id: int, account_id: Optional[int] = None) -> float:
        """Calculate total cost basis across holdings."""
        with self.session_factory() as session:
            statement = select(Holding).where(Holding.user_id == user_id)

            if account_id is not None:
                statement = statement.where(Holding.account_id == account_id)

            holdings = session.exec(statement).all()
            return sum(h.quantity * h.avg_price for h in holdings)

    def upsert_by_symbol(self, holding: Holding, *, user_id: int) -> Holding:
        """Insert or update a holding by symbol.

        When account_id is None, only matches holdings with NULL account_id
        to avoid unintended updates across different accounts.
        """
        with self.session_factory() as session:
            statement = select(Holding).where(
                Holding.symbol == holding.symbol, Holding.user_id == user_id
            )

            # Explicitly handle None to avoid ambiguous matches
            if holding.account_id is not None:
                statement = statement.where(Holding.account_id == holding.account_id)
            else:
                statement = statement.where(Holding.account_id.is_(None))  # type: ignore

            existing = session.exec(statement).first()

            if existing:
                # Update existing
                existing.user_id = user_id
                existing.quantity = holding.quantity
                existing.avg_price = holding.avg_price
                existing.acquired_at = holding.acquired_at
                existing.currency = holding.currency
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # Insert new
                holding.user_id = user_id
                session.add(holding)
                session.commit()
                session.refresh(holding)
                return holding

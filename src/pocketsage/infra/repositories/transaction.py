"""SQLModel implementation of Transaction repository."""

from __future__ import annotations

from datetime import datetime
from typing import Callable, Optional

from sqlmodel import Session, select

from ...models.transaction import Transaction


class SQLModelTransactionRepository:
    """SQLModel-based transaction repository implementation."""

    def __init__(self, session_factory: Callable[[], Session]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    def get_by_id(self, transaction_id: int, *, user_id: int) -> Optional[Transaction]:
        """Retrieve a transaction by ID."""
        with self.session_factory() as session:
            obj = session.exec(
                select(Transaction)
                .where(Transaction.id == transaction_id)
                .where(Transaction.user_id == user_id)
            ).first()
            if obj:
                session.expunge(obj)
            return obj

    def list_all(self, *, user_id: int, limit: int = 100, offset: int = 0) -> list[Transaction]:
        """List all transactions with pagination."""
        with self.session_factory() as session:
            statement = (
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
                .offset(offset)
                .limit(limit)
            )
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def filter_by_date_range(
        self, start_date: datetime, end_date: datetime, *, user_id: int
    ) -> list[Transaction]:
        """Get transactions within a date range."""
        with self.session_factory() as session:
            statement = (
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .where(Transaction.occurred_at >= start_date)
                .where(Transaction.occurred_at <= end_date)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
            )
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def filter_by_account(self, account_id: int, *, user_id: int) -> list[Transaction]:
        """Get all transactions for a specific account."""
        with self.session_factory() as session:
            statement = (
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .where(Transaction.account_id == account_id)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
            )
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def filter_by_category(self, category_id: int, *, user_id: int) -> list[Transaction]:
        """Get all transactions for a specific category."""
        with self.session_factory() as session:
            statement = (
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .where(Transaction.category_id == category_id)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
            )
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def list_by_liability(self, liability_id: int, *, user_id: int) -> list[Transaction]:
        """List transactions tied to a liability."""
        with self.session_factory() as session:
            statement = (
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .where(Transaction.liability_id == liability_id)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
            )
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def search(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        text: Optional[str] = None,
        user_id: int,
    ) -> list[Transaction]:
        """Advanced search with multiple filters."""
        with self.session_factory() as session:
            statement = select(Transaction)
            statement = statement.where(Transaction.user_id == user_id)

            if start_date:
                statement = statement.where(Transaction.occurred_at >= start_date)
            if end_date:
                statement = statement.where(Transaction.occurred_at <= end_date)
            if account_id:
                statement = statement.where(Transaction.account_id == account_id)
            if category_id:
                statement = statement.where(Transaction.category_id == category_id)
            if text:
                statement = statement.where(Transaction.memo.contains(text))  # type: ignore

            statement = statement.order_by(Transaction.occurred_at.desc())  # type: ignore
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def create(self, transaction: Transaction, *, user_id: int) -> Transaction:
        """Create a new transaction."""
        with self.session_factory() as session:
            transaction.user_id = user_id
            session.add(transaction)
            session.commit()
            session.refresh(transaction)
            session.expunge(transaction)
            return transaction

    def update(self, transaction: Transaction, *, user_id: int) -> Transaction:
        """Update an existing transaction."""
        with self.session_factory() as session:
            transaction.user_id = user_id
            session.add(transaction)
            session.commit()
            session.refresh(transaction)
            session.expunge(transaction)
            return transaction

    def delete(self, transaction_id: int, *, user_id: int) -> None:
        """Delete a transaction by ID."""
        with self.session_factory() as session:
            transaction = session.exec(
                select(Transaction)
                .where(Transaction.id == transaction_id)
                .where(Transaction.user_id == user_id)
            ).first()
            if transaction:
                session.delete(transaction)
                session.commit()

    def get_monthly_summary(self, year: int, month: int, *, user_id: int) -> dict[str, float]:
        """Get income/expense summary for a month.

        Note: Uses naive datetimes matching the Transaction model's occurred_at field.
        The boundary logic uses [start, end) to correctly include all transactions
        within the month without overlap.
        """
        with self.session_factory() as session:
            # Create date range: first day at 00:00:00 to first day of next month at 00:00:00
            # This gives us [start, end) which includes all timestamps in the target month
            start_date = datetime(year, month, 1, 0, 0, 0, 0)
            if month == 12:
                end_date = datetime(year + 1, 1, 1, 0, 0, 0, 0)
            else:
                end_date = datetime(year, month + 1, 1, 0, 0, 0, 0)

            statement = (
                select(Transaction)
                .where(Transaction.user_id == user_id)
                .where(Transaction.occurred_at >= start_date)
                .where(Transaction.occurred_at < end_date)  # Exclusive end boundary
            )
            transactions = session.exec(statement).all()

            income = sum(t.amount for t in transactions if t.amount > 0)
            expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)

            return {
                "income": income,
                "expenses": expenses,
                "net": income - expenses,
            }

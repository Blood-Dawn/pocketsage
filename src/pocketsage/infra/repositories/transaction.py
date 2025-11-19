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

    def get_by_id(self, transaction_id: int) -> Optional[Transaction]:
        """Retrieve a transaction by ID."""
        with self.session_factory() as session:
            return session.get(Transaction, transaction_id)

    def list_all(self, limit: int = 100, offset: int = 0) -> list[Transaction]:
        """List all transactions with pagination."""
        with self.session_factory() as session:
            statement = select(Transaction).order_by(Transaction.occurred_at.desc()).offset(offset).limit(limit)  # type: ignore
            return list(session.exec(statement).all())

    def filter_by_date_range(
        self, start_date: datetime, end_date: datetime
    ) -> list[Transaction]:
        """Get transactions within a date range."""
        with self.session_factory() as session:
            statement = (
                select(Transaction)
                .where(Transaction.occurred_at >= start_date)
                .where(Transaction.occurred_at <= end_date)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
            )
            return list(session.exec(statement).all())

    def filter_by_account(self, account_id: int) -> list[Transaction]:
        """Get all transactions for a specific account."""
        with self.session_factory() as session:
            statement = (
                select(Transaction)
                .where(Transaction.account_id == account_id)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
            )
            return list(session.exec(statement).all())

    def filter_by_category(self, category_id: int) -> list[Transaction]:
        """Get all transactions for a specific category."""
        with self.session_factory() as session:
            statement = (
                select(Transaction)
                .where(Transaction.category_id == category_id)
                .order_by(Transaction.occurred_at.desc())  # type: ignore
            )
            return list(session.exec(statement).all())

    def search(
        self,
        *,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        account_id: Optional[int] = None,
        category_id: Optional[int] = None,
        text: Optional[str] = None,
    ) -> list[Transaction]:
        """Advanced search with multiple filters."""
        with self.session_factory() as session:
            statement = select(Transaction)

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
            return list(session.exec(statement).all())

    def create(self, transaction: Transaction) -> Transaction:
        """Create a new transaction."""
        with self.session_factory() as session:
            session.add(transaction)
            session.commit()
            session.refresh(transaction)
            return transaction

    def update(self, transaction: Transaction) -> Transaction:
        """Update an existing transaction."""
        with self.session_factory() as session:
            session.add(transaction)
            session.commit()
            session.refresh(transaction)
            return transaction

    def delete(self, transaction_id: int) -> None:
        """Delete a transaction by ID."""
        with self.session_factory() as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction:
                session.delete(transaction)
                session.commit()

    def get_monthly_summary(self, year: int, month: int) -> dict[str, float]:
        """Get income/expense summary for a month."""
        with self.session_factory() as session:
            # Create date range for the month
            start_date = datetime(year, month, 1)
            if month == 12:
                end_date = datetime(year + 1, 1, 1)
            else:
                end_date = datetime(year, month + 1, 1)

            statement = (
                select(Transaction)
                .where(Transaction.occurred_at >= start_date)
                .where(Transaction.occurred_at < end_date)
            )
            transactions = session.exec(statement).all()

            income = sum(t.amount for t in transactions if t.amount > 0)
            expenses = sum(abs(t.amount) for t in transactions if t.amount < 0)

            return {
                "income": income,
                "expenses": expenses,
                "net": income - expenses,
            }

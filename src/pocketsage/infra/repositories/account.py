"""SQLModel implementation of Account repository."""

from __future__ import annotations

from typing import Callable, Optional

from sqlmodel import Session, select

from ...models.account import Account
from ...models.transaction import Transaction


class SQLModelAccountRepository:
    """SQLModel-based account repository implementation."""

    def __init__(self, session_factory: Callable[[], Session]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    def get_by_id(self, account_id: int) -> Optional[Account]:
        """Retrieve an account by ID."""
        with self.session_factory() as session:
            return session.get(Account, account_id)

    def get_by_name(self, name: str) -> Optional[Account]:
        """Retrieve an account by name."""
        with self.session_factory() as session:
            statement = select(Account).where(Account.name == name)
            return session.exec(statement).first()

    def list_all(self) -> list[Account]:
        """List all accounts."""
        with self.session_factory() as session:
            statement = select(Account).order_by(Account.name)  # type: ignore
            return list(session.exec(statement).all())

    def create(self, account: Account) -> Account:
        """Create a new account."""
        with self.session_factory() as session:
            session.add(account)
            session.commit()
            session.refresh(account)
            return account

    def update(self, account: Account) -> Account:
        """Update an existing account."""
        with self.session_factory() as session:
            session.add(account)
            session.commit()
            session.refresh(account)
            return account

    def delete(self, account_id: int) -> None:
        """Delete an account by ID."""
        with self.session_factory() as session:
            account = session.get(Account, account_id)
            if account:
                session.delete(account)
                session.commit()

    def get_balance(self, account_id: int) -> float:
        """Calculate current balance for an account."""
        with self.session_factory() as session:
            statement = select(Transaction).where(Transaction.account_id == account_id)
            transactions = session.exec(statement).all()
            return sum(t.amount for t in transactions)

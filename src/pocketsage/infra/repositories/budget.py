"""SQLModel implementation of Budget repository."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Callable, Optional

from sqlmodel import Session, select

from ...models.budget import Budget, BudgetLine


class SQLModelBudgetRepository:
    """SQLModel-based budget repository implementation."""

    def __init__(self, session_factory: Callable[[], Session]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    def get_by_id(self, budget_id: int) -> Optional[Budget]:
        """Retrieve a budget by ID."""
        with self.session_factory() as session:
            return session.get(Budget, budget_id)

    def get_by_period(self, start_date: date, end_date: date) -> Optional[Budget]:
        """Get budget for a specific period."""
        with self.session_factory() as session:
            statement = (
                select(Budget)
                .where(Budget.period_start == start_date)
                .where(Budget.period_end == end_date)
            )
            return session.exec(statement).first()

    def get_for_month(self, year: int, month: int) -> Optional[Budget]:
        """Get budget for a specific month."""
        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        with self.session_factory() as session:
            statement = (
                select(Budget)
                .where(Budget.period_start <= start_date)
                .where(Budget.period_end >= end_date)
            )
            return session.exec(statement).first()

    def list_all(self) -> list[Budget]:
        """List all budgets."""
        with self.session_factory() as session:
            statement = select(Budget).order_by(Budget.period_start.desc())  # type: ignore
            return list(session.exec(statement).all())

    def create(self, budget: Budget) -> Budget:
        """Create a new budget."""
        with self.session_factory() as session:
            session.add(budget)
            session.commit()
            session.refresh(budget)
            return budget

    def update(self, budget: Budget) -> Budget:
        """Update an existing budget."""
        with self.session_factory() as session:
            session.add(budget)
            session.commit()
            session.refresh(budget)
            return budget

    def delete(self, budget_id: int) -> None:
        """Delete a budget by ID."""
        with self.session_factory() as session:
            budget = session.get(Budget, budget_id)
            if budget:
                session.delete(budget)
                session.commit()

    # Budget line operations
    def get_line_by_id(self, line_id: int) -> Optional[BudgetLine]:
        """Get a specific budget line."""
        with self.session_factory() as session:
            return session.get(BudgetLine, line_id)

    def get_lines_for_budget(self, budget_id: int) -> list[BudgetLine]:
        """Get all lines for a budget."""
        with self.session_factory() as session:
            statement = select(BudgetLine).where(BudgetLine.budget_id == budget_id)
            return list(session.exec(statement).all())

    def create_line(self, line: BudgetLine) -> BudgetLine:
        """Create a new budget line."""
        with self.session_factory() as session:
            session.add(line)
            session.commit()
            session.refresh(line)
            return line

    def update_line(self, line: BudgetLine) -> BudgetLine:
        """Update a budget line."""
        with self.session_factory() as session:
            session.add(line)
            session.commit()
            session.refresh(line)
            return line

    def delete_line(self, line_id: int) -> None:
        """Delete a budget line."""
        with self.session_factory() as session:
            line = session.get(BudgetLine, line_id)
            if line:
                session.delete(line)
                session.commit()

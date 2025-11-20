"""SQLModel implementation of Budget repository."""

from __future__ import annotations

from calendar import monthrange
from datetime import date
from typing import Callable, Optional

from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

from ...models.budget import Budget, BudgetLine


class SQLModelBudgetRepository:
    """SQLModel-based budget repository implementation."""

    def __init__(self, session_factory: Callable[[], Session]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    def get_by_id(self, budget_id: int, *, user_id: int) -> Optional[Budget]:
        """Retrieve a budget by ID."""
        with self.session_factory() as session:
            statement = (
                select(Budget)
                .options(selectinload(Budget.lines))
                .where(Budget.id == budget_id)
                .where(Budget.user_id == user_id)
            )
            return session.exec(statement).first()

    def get_by_period(self, start_date: date, end_date: date, *, user_id: int) -> Optional[Budget]:
        """Get budget for a specific period."""
        with self.session_factory() as session:
            statement = (
                select(Budget)
                .where(Budget.user_id == user_id)
                .where(Budget.period_start == start_date)
                .where(Budget.period_end == end_date)
                .options(selectinload(Budget.lines))
            )
            return session.exec(statement).first()

    def get_for_month(self, year: int, month: int, *, user_id: int) -> Optional[Budget]:
        """Get budget for a specific month.

        Returns the budget that exactly matches the month boundaries to avoid
        returning budgets that span multiple months.
        """
        start_date = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end_date = date(year, month, last_day)

        with self.session_factory() as session:
            # Use exact match to avoid overlapping periods
            statement = (
                select(Budget)
                .where(Budget.user_id == user_id)
                .where(Budget.period_start == start_date)
                .where(Budget.period_end == end_date)
                .options(selectinload(Budget.lines))
            )
            return session.exec(statement).first()

    def list_all(self, *, user_id: int) -> list[Budget]:
        """List all budgets."""
        with self.session_factory() as session:
            statement = (
                select(Budget)
                .where(Budget.user_id == user_id)
                .options(selectinload(Budget.lines))
                .order_by(Budget.period_start.desc())
            )  # type: ignore
            return list(session.exec(statement).all())

    def create(self, budget: Budget, *, user_id: int) -> Budget:
        """Create a new budget."""
        with self.session_factory() as session:
            budget.user_id = user_id
            session.add(budget)
            session.commit()
            session.refresh(budget)
            session.expunge(budget)
            return budget

    def update(self, budget: Budget, *, user_id: int) -> Budget:
        """Update an existing budget."""
        with self.session_factory() as session:
            budget.user_id = user_id
            session.add(budget)
            session.commit()
            session.refresh(budget)
            session.expunge(budget)
            return budget

    def delete(self, budget_id: int, *, user_id: int) -> None:
        """Delete a budget by ID."""
        with self.session_factory() as session:
            budget = session.exec(
                select(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
            ).first()
            if budget:
                session.delete(budget)
                session.commit()

    # Budget line operations
    def get_line_by_id(self, line_id: int, *, user_id: int) -> Optional[BudgetLine]:
        """Get a specific budget line."""
        with self.session_factory() as session:
            line = session.exec(
                select(BudgetLine).where(BudgetLine.id == line_id, BudgetLine.user_id == user_id)
            ).first()
            return line

    def get_lines_for_budget(self, budget_id: int, *, user_id: int) -> list[BudgetLine]:
        """Get all lines for a budget."""
        with self.session_factory() as session:
            statement = select(BudgetLine).where(
                BudgetLine.budget_id == budget_id, BudgetLine.user_id == user_id
            )
            return list(session.exec(statement).all())

    def create_line(self, line: BudgetLine, *, user_id: int) -> BudgetLine:
        """Create a new budget line."""
        with self.session_factory() as session:
            line.user_id = user_id
            session.add(line)
            session.commit()
            session.refresh(line)
            session.expunge(line)
            return line

    def update_line(self, line: BudgetLine, *, user_id: int) -> BudgetLine:
        """Update a budget line."""
        with self.session_factory() as session:
            line.user_id = user_id
            session.add(line)
            session.commit()
            session.refresh(line)
            session.expunge(line)
            return line

    def delete_line(self, line_id: int, *, user_id: int) -> None:
        """Delete a budget line."""
        with self.session_factory() as session:
            line = session.exec(
                select(BudgetLine).where(BudgetLine.id == line_id, BudgetLine.user_id == user_id)
            ).first()
            if line:
                session.delete(line)
                session.commit()

"""Budget repository protocol."""

from __future__ import annotations

from datetime import date
from typing import Optional, Protocol

from ...models.budget import Budget, BudgetLine


class BudgetRepository(Protocol):
    """Repository for managing budget entities."""

    def get_by_id(self, budget_id: int) -> Optional[Budget]:
        """Retrieve a budget by ID."""
        ...

    def get_by_period(self, start_date: date, end_date: date) -> Optional[Budget]:
        """Get budget for a specific period."""
        ...

    def get_for_month(self, year: int, month: int) -> Optional[Budget]:
        """Get budget for a specific month."""
        ...

    def list_all(self) -> list[Budget]:
        """List all budgets."""
        ...

    def create(self, budget: Budget) -> Budget:
        """Create a new budget."""
        ...

    def update(self, budget: Budget) -> Budget:
        """Update an existing budget."""
        ...

    def delete(self, budget_id: int) -> None:
        """Delete a budget by ID."""
        ...

    # Budget line operations
    def get_line_by_id(self, line_id: int) -> Optional[BudgetLine]:
        """Get a specific budget line."""
        ...

    def get_lines_for_budget(self, budget_id: int) -> list[BudgetLine]:
        """Get all lines for a budget."""
        ...

    def create_line(self, line: BudgetLine) -> BudgetLine:
        """Create a new budget line."""
        ...

    def update_line(self, line: BudgetLine) -> BudgetLine:
        """Update a budget line."""
        ...

    def delete_line(self, line_id: int) -> None:
        """Delete a budget line."""
        ...

"""Category repository protocol."""

from __future__ import annotations

from typing import Optional, Protocol

from ...models.category import Category


class CategoryRepository(Protocol):
    """Repository for managing category entities."""

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Retrieve a category by ID."""
        ...

    def get_by_slug(self, slug: str) -> Optional[Category]:
        """Retrieve a category by slug."""
        ...

    def list_all(self) -> list[Category]:
        """List all categories."""
        ...

    def list_by_type(self, category_type: str) -> list[Category]:
        """List categories filtered by type (income/expense)."""
        ...

    def create(self, category: Category) -> Category:
        """Create a new category."""
        ...

    def update(self, category: Category) -> Category:
        """Update an existing category."""
        ...

    def delete(self, category_id: int) -> None:
        """Delete a category by ID."""
        ...

    def upsert_by_slug(self, category: Category) -> Category:
        """Insert or update a category by slug."""
        ...

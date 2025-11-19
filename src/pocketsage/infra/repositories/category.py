"""SQLModel implementation of Category repository."""

from __future__ import annotations

from typing import Callable, Optional

from sqlmodel import Session, select

from ...models.category import Category


class SQLModelCategoryRepository:
    """SQLModel-based category repository implementation."""

    def __init__(self, session_factory: Callable[[], Session]):
        """Initialize with a session factory."""
        self.session_factory = session_factory

    def get_by_id(self, category_id: int) -> Optional[Category]:
        """Retrieve a category by ID."""
        with self.session_factory() as session:
            return session.get(Category, category_id)

    def get_by_slug(self, slug: str) -> Optional[Category]:
        """Retrieve a category by slug."""
        with self.session_factory() as session:
            statement = select(Category).where(Category.slug == slug)
            return session.exec(statement).first()

    def list_all(self) -> list[Category]:
        """List all categories."""
        with self.session_factory() as session:
            statement = select(Category).order_by(Category.name)  # type: ignore
            return list(session.exec(statement).all())

    def list_by_type(self, category_type: str) -> list[Category]:
        """List categories filtered by type (income/expense)."""
        with self.session_factory() as session:
            statement = (
                select(Category)
                .where(Category.category_type == category_type)
                .order_by(Category.name)  # type: ignore
            )
            return list(session.exec(statement).all())

    def create(self, category: Category) -> Category:
        """Create a new category."""
        with self.session_factory() as session:
            session.add(category)
            session.commit()
            session.refresh(category)
            return category

    def update(self, category: Category) -> Category:
        """Update an existing category."""
        with self.session_factory() as session:
            session.add(category)
            session.commit()
            session.refresh(category)
            return category

    def delete(self, category_id: int) -> None:
        """Delete a category by ID."""
        with self.session_factory() as session:
            if category := session.get(Category, category_id):
                session.delete(category)
                session.commit()

    def upsert_by_slug(self, category: Category) -> Category:
        """Insert or update a category by slug.

        Updates all mutable fields (name, category_type, color).
        The slug field is used for matching and is not updated.
        """
        with self.session_factory() as session:
            existing = session.exec(
                select(Category).where(Category.slug == category.slug)
            ).first()

            if existing:
                # Update all mutable fields (slug is the match key, so not updated)
                existing.name = category.name
                existing.category_type = category.category_type
                existing.color = category.color
                session.add(existing)
                session.commit()
                session.refresh(existing)
                return existing
            else:
                # Insert new
                session.add(category)
                session.commit()
                session.refresh(category)
                return category

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

    def get_by_id(self, category_id: int, *, user_id: int) -> Optional[Category]:
        """Retrieve a category by ID."""
        with self.session_factory() as session:
            obj = session.exec(
                select(Category).where(Category.id == category_id, Category.user_id == user_id)
            ).first()
            if obj:
                session.refresh(obj)
                session.expunge(obj)
            return obj

    def get_by_slug(self, slug: str, *, user_id: int) -> Optional[Category]:
        """Retrieve a category by slug."""
        with self.session_factory() as session:
            statement = select(Category).where(Category.slug == slug, Category.user_id == user_id)
            obj = session.exec(statement).first()
            if obj:
                session.refresh(obj)
                session.expunge(obj)
            return obj

    def list_all(self, *, user_id: int) -> list[Category]:
        """List all categories."""
        with self.session_factory() as session:
            statement = (
                select(Category)
                .where(Category.user_id == user_id)
                .order_by(Category.name)  # type: ignore
            )
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def list_by_type(self, category_type: str, *, user_id: int) -> list[Category]:
        """List categories filtered by type (income/expense)."""
        with self.session_factory() as session:
            statement = (
                select(Category)
                .where(Category.user_id == user_id)
                .where(Category.category_type == category_type)
                .order_by(Category.name)  # type: ignore
            )
            rows = list(session.exec(statement).all())
            session.expunge_all()
            return rows

    def create(self, category: Category, *, user_id: int) -> Category:
        """Create a new category."""
        with self.session_factory() as session:
            category.user_id = user_id
            session.add(category)
            session.commit()
            session.refresh(category)
            session.expunge(category)
            return category

    def update(self, category: Category, *, user_id: int) -> Category:
        """Update an existing category."""
        with self.session_factory() as session:
            category.user_id = user_id
            session.add(category)
            session.commit()
            session.refresh(category)
            session.expunge(category)
            return category

    def delete(self, category_id: int, *, user_id: int) -> None:
        """Delete a category by ID."""
        with self.session_factory() as session:
            category = session.exec(
                select(Category).where(Category.id == category_id, Category.user_id == user_id)
            ).first()
            if category:
                session.delete(category)
                session.commit()

    def upsert_by_slug(self, category: Category, *, user_id: int) -> Category:
        """Insert or update a category by slug.

        Updates all mutable fields (name, category_type, color).
        The slug field is used for matching and is not updated.
        """
        with self.session_factory() as session:
            existing = session.exec(
                select(Category).where(Category.slug == category.slug, Category.user_id == user_id)
            ).first()

            if existing:
                # Update all mutable fields (slug is the match key, so not updated)
                existing.name = category.name
                existing.category_type = category.category_type
                existing.color = category.color
                existing.user_id = user_id
                session.add(existing)
                session.commit()
                session.refresh(existing)
                session.expunge(existing)
                return existing
            else:
                # Insert new
                category.user_id = user_id
                session.add(category)
                session.commit()
                session.refresh(category)
                session.expunge(category)
                return category

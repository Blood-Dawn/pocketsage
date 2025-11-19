"""Database infrastructure for desktop app."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlmodel import Session, SQLModel, create_engine

from ..config import BaseConfig


def create_db_engine(config: BaseConfig):
    """Create SQLModel engine from configuration."""
    engine_options = config.sqlalchemy_engine_options()
    engine = create_engine(config.DATABASE_URL, **engine_options)
    return engine


def init_database(engine) -> None:
    """Initialize database schema."""
    # Import all models to ensure they're registered
    from .. import models  # noqa: F401

    SQLModel.metadata.create_all(engine)


@contextmanager
def session_scope(engine) -> Iterator[Session]:
    """Provide a transactional scope around operations."""
    session = Session(engine)
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_session_factory(engine):
    """Create a session factory function."""

    @contextmanager
    def factory() -> Iterator[Session]:
        """Create a new session."""
        session = Session(engine)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    return factory

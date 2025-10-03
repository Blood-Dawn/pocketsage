"""Database and extension wiring for PocketSage."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from flask import Flask, g
from sqlmodel import Session, SQLModel, create_engine

from . import models  # noqa: F401  # ensure models registered with SQLModel metadata
from .config import BaseConfig

_engine = None


def init_db(app: Flask) -> None:
    """Initialize the SQLModel engine using configuration from the app."""

    config: BaseConfig = app.config["POCKETSAGE_CONFIG"]
    engine_options = app.config.get("SQLALCHEMY_ENGINE_OPTIONS", {})
    engine = create_engine(config.DATABASE_URL, **engine_options)

    global _engine
    _engine = engine

    @app.before_request
    def _prime_session() -> None:
        """Attach a scoped SQLModel session to the request context."""

        if "sqlmodel_session" not in g:
            g.sqlmodel_session = Session(engine)
            # TODO(@db-team): bulk seed default data when session boots.

    @app.teardown_appcontext
    def _shutdown_session(exception: Exception | None) -> None:  # pragma: no cover
        session = g.pop("sqlmodel_session", None)
        if session is not None:
            session.close()

    with engine.begin() as connection:
        SQLModel.metadata.create_all(connection)
        # TODO(@migrations): replace with Alembic once schema stabilizes.


def get_engine():
    """Return the initialized SQLModel engine."""

    if _engine is None:  # pragma: no cover - exercised in integration tests
        raise RuntimeError("Database engine not initialized")
    return _engine


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional scope around operations."""

    session = Session(get_engine())
    try:
        yield session
        session.commit()
    except Exception:  # pragma: no cover - re-raised for caller to handle
        session.rollback()
        raise
    finally:
        session.close()
        # TODO(@qa-team): add tests covering rollback + retry semantics.

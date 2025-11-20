"""Demo data seeding script."""

from __future__ import annotations

from pocketsage.config import BaseConfig
from pocketsage.infra.database import create_db_engine, init_database, session_scope
from pocketsage.services.admin_tasks import run_demo_seed
from pocketsage.services import auth


def seed_demo() -> None:
    """Populate the database with demo content for the desktop app."""

    config = BaseConfig()
    engine = create_db_engine(config)
    init_database(engine)

    session_factory = lambda: session_scope(engine)
    user = None
    if not auth.any_users_exist(session_factory):
        user = auth.create_user(
            username="demo_admin",
            password="demo_admin",
            role="admin",
            session_factory=session_factory,
        )
    else:
        existing = auth.list_users(session_factory)
        user = existing[0]

    # Pass a session factory so seeding uses the same engine
    run_demo_seed(session_factory=session_factory, user_id=user.id, force=True)  # type: ignore[arg-type]


if __name__ == "__main__":
    seed_demo()

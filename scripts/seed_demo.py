"""Demo data seeding script."""

from __future__ import annotations

from pocketsage import create_app
from pocketsage.extensions import session_scope


def seed_demo() -> None:
    """Populate the database with demo content."""

    app = create_app("development")
    with app.app_context():
        with session_scope():
            # TODO(@admin-squad): insert demo transactions, habits, liabilities, and categories.
            raise NotImplementedError("Demo seed not yet implemented")


if __name__ == "__main__":
    seed_demo()

"""Authentication and user management services."""

from __future__ import annotations

from typing import Callable, Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from sqlmodel import Session, select

from ..models.user import User

SessionFactory = Callable[[], Session]

_hasher = PasswordHasher()
_ALLOWED_ROLES = {"user", "admin"}


def _normalize_role(role: str) -> str:
    role = (role or "user").lower()
    if role not in _ALLOWED_ROLES:
        raise ValueError(f"Invalid role: {role}")
    return role


def list_users(session_factory: SessionFactory) -> list[User]:
    """Return all users ordered by creation time."""
    with session_factory() as session:
        users = list(session.exec(select(User).order_by(User.created_at)).all())
        session.expunge_all()
    return users


def get_user_by_username(username: str, session_factory: SessionFactory) -> Optional[User]:
    """Fetch a user by username."""
    with session_factory() as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user:
            session.expunge(user)
        return user


def any_users_exist(session_factory: SessionFactory) -> bool:
    """Determine if any users exist for bootstrapping login/onboarding."""
    with session_factory() as session:
        return session.exec(select(User.id)).first() is not None


def create_user(
    *,
    username: str,
    password: str,
    role: str = "user",
    session_factory: SessionFactory,
) -> User:
    """Create a new user with hashed password."""

    normalized_role = _normalize_role(role)
    password_hash = _hasher.hash(password)
    with session_factory() as session:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            raise ValueError("Username already exists")
        user = User(username=username, password_hash=password_hash, role=normalized_role)
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def authenticate(
    *,
    username: str,
    password: str,
    session_factory: SessionFactory,
) -> Optional[User]:
    """Validate credentials and return the user when correct."""

    with session_factory() as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            return None
        try:
            _hasher.verify(user.password_hash, password)
        except VerifyMismatchError:
            return None

        session.refresh(user)
        user.last_login = user.last_login or user.created_at
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def set_role(*, user_id: int, role: str, session_factory: SessionFactory) -> User:
    """Update the role for a user."""

    normalized_role = _normalize_role(role)
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        user.role = normalized_role
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user

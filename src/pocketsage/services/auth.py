"""Authentication and user management services."""
# TODO(@pocketsage-auth): Reintroduce real multi-user auth in a future phase if needed.

from __future__ import annotations

from typing import Callable, Optional

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHash, VerificationError, VerifyMismatchError
from sqlmodel import Session, select

from ..models.user import User

SessionFactory = Callable[[], Session]

_hasher = PasswordHasher()
_ALLOWED_ROLES = {"user", "admin", "guest"}
GUEST_USERNAME = "guest"
LOCAL_USERNAME = "local"
LOCAL_ROLE = "admin"


def _is_guest_username(username: str) -> bool:
    """Return True when the username is reserved for guest sessions."""

    return username.strip().lower() == GUEST_USERNAME


def _normalize_role(role: str) -> str:
    role = (role or "user").lower()
    if role not in _ALLOWED_ROLES:
        raise ValueError(f"Invalid role: {role}")
    return role


def list_users(session_factory: SessionFactory) -> list[User]:
    """Return all users ordered by creation time."""
    with session_factory() as session:
        users = list(
            session.exec(
                select(User).where(User.username != GUEST_USERNAME).order_by(User.created_at)
            ).all()
        )
        session.expunge_all()
    return users


def get_user_by_username(username: str, session_factory: SessionFactory) -> Optional[User]:
    """Fetch a user by username."""
    username = username.strip()
    with session_factory() as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user:
            session.expunge(user)
        return user


def any_users_exist(session_factory: SessionFactory) -> bool:
    """Determine if any users exist for bootstrapping login/onboarding."""
    with session_factory() as session:
        return (
            session.exec(select(User.id).where(User.username != GUEST_USERNAME)).first()
            is not None
        )


def create_user(
    *,
    username: str,
    password: str,
    role: str = "user",
    session_factory: SessionFactory,
) -> User:
    """Create a new user with hashed password."""

    normalized_role = _normalize_role(role)
    username = username.strip()
    if _is_guest_username(username):
        raise ValueError("The guest account is reserved for temporary sessions.")
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

    username = username.strip()
    if not username:
        return None
    with session_factory() as session:
        user = session.exec(select(User).where(User.username == username)).first()
        if user is None:
            return None
        try:
            _hasher.verify(user.password_hash, password)
        except (VerifyMismatchError, InvalidHash, VerificationError):
            return None

        session.refresh(user)
        user.last_login = user.last_login or user.created_at
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user


def ensure_guest_user(session_factory: SessionFactory) -> User:
    """Create or return the reserved guest user for temporary sessions."""

    with session_factory() as session:
        guest = session.exec(select(User).where(User.username == GUEST_USERNAME)).first()
        if guest:
            session.expunge(guest)
            return guest
        password_hash = _hasher.hash(GUEST_USERNAME)
        guest = User(username=GUEST_USERNAME, password_hash=password_hash, role="guest")
        session.add(guest)
        session.flush()
        session.refresh(guest)
        session.expunge(guest)
        return guest


def ensure_local_user(session_factory: SessionFactory) -> User:
    """Create or return the default local profile (passwordless desktop mode)."""

    with session_factory() as session:
        user = session.exec(select(User).where(User.username == LOCAL_USERNAME)).first()
        if user:
            session.expunge(user)
            return user
        password_hash = _hasher.hash(LOCAL_USERNAME)
        user = User(username=LOCAL_USERNAME, password_hash=password_hash, role=LOCAL_ROLE)
        session.add(user)
        session.flush()
        session.refresh(user)
        session.expunge(user)
        return user


def purge_guest_user(session_factory: SessionFactory) -> bool:
    """Delete guest user data so sessions never persist to disk."""

    from . import admin_tasks

    with session_factory() as session:
        guest = session.exec(select(User).where(User.username == GUEST_USERNAME)).first()
        if guest is None or guest.id is None:
            return False
        guest_id = guest.id

    try:
        admin_tasks.reset_demo_database(user_id=guest_id, session_factory=session_factory, reseed=False)
    except Exception:
        # Best-effort cleanup; schema mismatches or missing tables should not block login.
        pass
    try:
        with session_factory() as session:
            guest = session.get(User, guest_id)
            if guest:
                session.delete(guest)
            session.flush()
            session.commit()
        return True
    except Exception:
        # Best-effort teardown; consider the purge successful even if deletion fails.
        return True


def start_guest_session(session_factory: SessionFactory) -> User:
    """Reset any prior guest data and return a fresh guest user instance."""

    purge_guest_user(session_factory)
    return ensure_guest_user(session_factory)


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


def reset_password(*, user_id: int, password: str, session_factory: SessionFactory) -> User:
    """Reset a user's password to the provided value."""

    if not password:
        raise ValueError("Password cannot be empty")
    password_hash = _hasher.hash(password)
    with session_factory() as session:
        user = session.get(User, user_id)
        if user is None:
            raise ValueError("User not found")
        if _is_guest_username(user.username):
            raise ValueError("Cannot reset password for guest user")
        user.password_hash = password_hash
        session.add(user)
        session.commit()
        session.refresh(user)
        session.expunge(user)
        return user

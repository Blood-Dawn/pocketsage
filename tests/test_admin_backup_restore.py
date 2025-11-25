from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import flet as ft
import pytest
from pocketsage.config import BaseConfig
from pocketsage.desktop.views import admin
from pocketsage.infra.database import create_db_engine, init_database, session_scope
from pocketsage.services import admin_tasks, auth


class _PageStub:
    def __init__(self):
        self.route = "/admin"
        self.snack_bar = None
        self.dialog = None
        self.overlay: list[ft.Control] = []

    def go(self, route: str):
        self.route = route

    def update(self):
        return None


@pytest.fixture()
def ctx(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "instance"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{data_dir/'admin.db'}")
    page = _PageStub()
    config = BaseConfig()
    engine = create_db_engine(config)
    init_database(engine)

    def factory():
        return session_scope(engine)

    user = auth.ensure_local_user(factory)
    context = SimpleNamespace(
        admin_mode=True,
        current_user=user,
        page=page,
        config=config,
        session_factory=factory,
        require_user_id=lambda: user.id,
    )
    return context, page, engine


def test_build_admin_view_renders_with_overlay(ctx):
    context, page, _engine = ctx
    view = admin.build_admin_view(context, page)
    assert view.route == "/admin"
    assert page.overlay  # file pickers attached


def test_backup_and_restore_round_trip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    data_dir = tmp_path / "instance"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{data_dir/'pocketsage.db'}")
    config = BaseConfig()
    engine = create_db_engine(config)
    init_database(engine)
    factory = lambda: session_scope(engine)
    user = auth.ensure_local_user(factory)

    # Seed a transaction so backup has content
    admin_tasks.run_demo_seed(session_factory=factory, user_id=user.id)

    backup_dir = data_dir / "backups"
    backup_path = admin_tasks.backup_database(backup_dir, config=config)
    assert backup_path.exists()

    restored_db = admin_tasks.restore_database(backup_path, config=config, confirm=True)
    assert restored_db.exists()


def test_restore_database_requires_confirm(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Safety check: restore_database should require confirm=True when overwriting."""
    data_dir = tmp_path / "instance"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(data_dir))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{data_dir/'pocketsage.db'}")
    config = BaseConfig()
    engine = create_db_engine(config)
    init_database(engine)

    def factory():
        return session_scope(engine)

    user = auth.ensure_local_user(factory)

    admin_tasks.run_demo_seed(session_factory=factory, user_id=user.id)

    backup_dir = data_dir / "backups"
    backup_path = admin_tasks.backup_database(backup_dir, config=config)

    # Calling without confirm=True should raise ValueError when overwriting
    with pytest.raises(ValueError, match="explicit confirmation"):
        admin_tasks.restore_database(backup_path, config=config)

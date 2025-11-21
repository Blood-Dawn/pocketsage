from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pocketsage.config import BaseConfig
from pocketsage.infra.database import create_db_engine, init_database, session_scope
from pocketsage.models import Transaction
from pocketsage.services import auth
from pocketsage.services.admin_tasks import (
    EXPORT_RETENTION,
    reset_demo_database,
    run_demo_seed,
    run_export,
)
from sqlmodel import delete, select


@pytest.fixture()
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "demo.db"
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    config = BaseConfig()
    engine = create_db_engine(config)
    init_database(engine)

    def base_factory():
        return session_scope(engine)

    user = auth.create_user(
        username="admin",
        password="password",
        role="admin",
        session_factory=base_factory,
    )

    def factory():
        return session_scope(engine)

    return factory, engine, user


def test_run_demo_seed_populates_sample_data(session_factory):
    factory, engine, user = session_factory

    summary = run_demo_seed(session_factory=factory, user_id=user.id)

    with session_scope(engine) as session:
        memos = [tx.memo for tx in session.exec(select(Transaction)).all()]

    assert len(memos) >= 6
    assert {"Grocery Run", "Dinner with friends", "Electric bill", "Monthly salary"}.issubset(
        set(memos)
    )
    assert summary.transactions == len(memos)
    assert summary.categories >= 6
    assert summary.accounts >= 2

    # Idempotent: rerun should not duplicate
    rerun = run_demo_seed(session_factory=factory, user_id=user.id)
    with session_scope(engine) as session:
        count_after = len(session.exec(select(Transaction)).all())
    assert count_after == len(memos)
    assert rerun.transactions == summary.transactions


def test_run_export_creates_zip_and_prunes_old(session_factory, tmp_path: Path):
    factory, engine, user = session_factory
    run_demo_seed(session_factory=factory, user_id=user.id)

    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    now = datetime.now(timezone.utc)
    for index in range(EXPORT_RETENTION + 2):
        archive = exports_dir / f"pocketsage_export_20240101010{index}.zip"
        archive.write_bytes(b"old")
        old_time = (now - timedelta(days=index + 1)).timestamp()
        os.utime(archive, (old_time, old_time))

    created = run_export(exports_dir, session_factory=factory, user_id=user.id)
    assert created.exists()

    archives = sorted(exports_dir.glob("pocketsage_export_*.zip"))
    assert len(archives) == EXPORT_RETENTION
    assert created in archives


def test_reset_demo_database_restores_seed(session_factory):
    factory, engine, user = session_factory

    run_demo_seed(session_factory=factory, user_id=user.id)
    with session_scope(engine) as session:
        session.exec(delete(Transaction))

    reset_demo_database(session_factory=factory, user_id=user.id)

    with session_scope(engine) as session:
        count = len(session.exec(select(Transaction)).all())

    assert count >= 6


def test_reset_demo_database_drops_custom_rows(session_factory):
    factory, engine, user = session_factory

    run_demo_seed(session_factory=factory, user_id=user.id)
    with session_scope(engine) as session:
        session.add(
            Transaction(
                memo="Custom Row",
                amount=-12.34,
                occurred_at=datetime.now(timezone.utc),
                user_id=user.id,
            )
        )

    summary = reset_demo_database(session_factory=factory, user_id=user.id)

    with session_scope(engine) as session:
        memos = {tx.memo for tx in session.exec(select(Transaction)).all()}

    assert "Custom Row" not in memos
    assert summary.transactions == len(memos)


def test_guest_purge_isolation(session_factory):
    factory, engine, user = session_factory
    # Seed data for real user
    run_demo_seed(session_factory=factory, user_id=user.id)

    # Create guest and add a txn
    guest = auth.ensure_guest_user(session_factory=factory)
    with session_scope(engine) as session:
        session.add(
            Transaction(
                memo="Guest Tx",
                amount=-5.0,
                occurred_at=datetime.now(timezone.utc),
                user_id=guest.id,
            )
        )

    # Purge guest and ensure main user data unaffected
    assert auth.purge_guest_user(session_factory=factory)
    with session_scope(engine) as session:
        user_memos = {tx.memo for tx in session.exec(select(Transaction).where(Transaction.user_id == user.id))}
        guest_memos = list(session.exec(select(Transaction).where(Transaction.user_id == guest.id)))

    assert "Guest Tx" not in user_memos
    assert guest_memos == []

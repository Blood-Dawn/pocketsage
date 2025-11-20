from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pocketsage.config import BaseConfig
from pocketsage.infra.database import create_db_engine, init_database, session_scope
from pocketsage.models import Transaction
from pocketsage.services.admin_tasks import EXPORT_RETENTION, run_demo_seed, run_export
from sqlmodel import select


@pytest.fixture()
def session_factory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "demo.db"
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    config = BaseConfig()
    engine = create_db_engine(config)
    init_database(engine)

    def factory():
        return session_scope(engine)

    return factory, engine


def test_run_demo_seed_populates_sample_data(session_factory):
    factory, engine = session_factory

    run_demo_seed(session_factory=factory)

    with session_scope(engine) as session:
        memos = [tx.memo for tx in session.exec(select(Transaction)).all()]

    assert len(memos) >= 6
    assert {"Grocery Run", "Dinner with friends", "Electric bill", "Monthly salary"}.issubset(
        set(memos)
    )

    # Idempotent: rerun should not duplicate
    run_demo_seed(session_factory=factory)
    with session_scope(engine) as session:
        count_after = len(session.exec(select(Transaction)).all())
    assert count_after == len(memos)


def test_run_export_creates_zip_and_prunes_old(session_factory, tmp_path: Path):
    factory, engine = session_factory
    run_demo_seed(session_factory=factory)

    exports_dir = tmp_path / "exports"
    exports_dir.mkdir()

    now = datetime.now(timezone.utc)
    for index in range(EXPORT_RETENTION + 2):
        archive = exports_dir / f"pocketsage_export_20240101010{index}.zip"
        archive.write_bytes(b"old")
        old_time = (now - timedelta(days=index + 1)).timestamp()
        os.utime(archive, (old_time, old_time))

    created = run_export(exports_dir, session_factory=factory)
    assert created.exists()

    archives = sorted(exports_dir.glob("pocketsage_export_*.zip"))
    assert len(archives) == EXPORT_RETENTION
    assert created in archives

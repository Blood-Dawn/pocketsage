from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from pocketsage import create_app
from pocketsage.services.jobs import clear_jobs, set_async_execution


@pytest.fixture()
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")

    app = create_app("development")
    exports_dir = tmp_path / "exports"
    app.config.update(
        TESTING=True,
        POCKETSAGE_EXPORTS_DIR=str(exports_dir),
    )

    set_async_execution(False)
    clear_jobs()

    with app.test_client() as client:
        yield client

    set_async_execution(True)
    clear_jobs()


def _post_json(client, url: str, payload: dict[str, object]):
    return client.post(
        url,
        json=payload,
        headers={"Accept": "application/json"},
    )


def test_seed_demo_requires_confirmation(client):
    response = _post_json(client, "/admin/seed-demo", {"confirm": False})
    assert response.status_code == 400
    assert response.get_json()["error"] == "confirmation_required"


def test_seed_demo_job_lifecycle(client):
    response = _post_json(client, "/admin/seed-demo", {"confirm": True})
    assert response.status_code == 202
    job_data = response.get_json()
    assert job_data["status"] == "succeeded"

    # Poll job status endpoint
    status = client.get(f"/admin/jobs/{job_data['id']}", headers={"Accept": "application/json"})
    assert status.status_code == 200
    payload = status.get_json()
    assert payload["id"] == job_data["id"]
    assert payload["status"] == "succeeded"


def test_export_job_generates_zip_and_enforces_retention(client):
    exports_dir = Path(client.application.config["POCKETSAGE_EXPORTS_DIR"])
    exports_dir.mkdir(parents=True, exist_ok=True)

    # Create old archives to verify retention pruning keeps the newest five files.
    now = datetime.now(timezone.utc)
    for index in range(7):
        archive = exports_dir / f"pocketsage_export_20230101010{index}.zip"
        archive.write_bytes(b"test")
        old_time = now - timedelta(days=index + 1)
        mod_time = old_time.timestamp()
        os.utime(archive, (mod_time, mod_time))

    response = _post_json(client, "/admin/export", {})
    assert response.status_code == 202
    job_payload = response.get_json()
    assert job_payload["status"] == "succeeded"

    archives = sorted(exports_dir.glob("pocketsage_export_*.zip"))
    assert len(archives) == 5


def test_export_download_requires_archive(client):
    response = client.get("/admin/export/download")
    assert response.status_code == 302


def test_export_download_serves_latest_archive(client):
    client.post("/admin/export", json={}, headers={"Accept": "application/json"})
    response = client.get("/admin/export/download")
    assert response.status_code == 200
    assert "attachment" in response.headers.get("Content-Disposition", "")

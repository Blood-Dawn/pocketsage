"""Legacy smoke test placeholder."""

from __future__ import annotations

from pocketsage import create_app


def test_home_page_renders():
    app = create_app("development")
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 200
    assert b"Welcome to PocketSage" in response.data

"""Smoke tests for registered routes."""

from __future__ import annotations

import pytest
from pocketsage import create_app


@pytest.fixture
def client():
    app = create_app("development")
    app.config.update(TESTING=True)
    with app.test_client() as client:
        yield client


@pytest.mark.skip(
    reason="Route templates not yet implemented; see TODO(@qa-team) backlog item to re-enable."
)
@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/ledger/",
        "/ledger/new",
        "/habits/",
        "/habits/new",
        "/liabilities/",
        "/liabilities/new",
        "/portfolio/",
        "/portfolio/upload",
        "/admin/",
    ],
)
def test_routes_render(path, client):
    response = client.get(path)
    assert response.status_code == 200

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
    "path, expected_snippet",
    [
        ("/", None),
        ("/ledger/", None),
        ("/ledger/new", None),
        (
            "/habits/",
            "TODO(@habits-squad): render habits list with streak badges and toggle buttons.",
        ),
        ("/habits/new", None),
        ("/liabilities/", None),
        ("/liabilities/new", None),
        ("/portfolio/", None),
        ("/portfolio/upload", None),
        ("/admin/", None),
    ],
)
def test_routes_render(path, expected_snippet, client):
    response = client.get(path)
    assert response.status_code == 200
    if expected_snippet:
        body = response.get_data(as_text=True)
        assert expected_snippet in body

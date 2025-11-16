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
        "/overview/",
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


def test_admin_dashboard_includes_required_attributes(client):
    response = client.get("/admin/")
    assert response.status_code == 200

    html = response.data.decode("utf-8")

    # stats context renders ledger snapshot values
    assert "Total Transactions" in html
    assert "Last Transaction" in html

    # jobs payload and polling endpoint should be exposed via data attributes
    assert "data-admin-dashboard" in html
    assert 'data-job-status-endpoint="/admin/jobs/__JOB__"' in html
    assert "data-initial-jobs='[]'" in html

    # latest_export context should render the empty state when no export exists
    assert "No exports generated yet." in html

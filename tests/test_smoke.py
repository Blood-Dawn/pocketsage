"""Legacy smoke test placeholder."""

from __future__ import annotations

import pytest
from pocketsage import create_app


@pytest.mark.skip(
    reason="TODO(@qa-team): replace with entrypoint redirect test under new blueprint layout."
)
def test_home_redirect():
    app = create_app("development")
    client = app.test_client()
    response = client.get("/")
    assert response.status_code in (301, 302)

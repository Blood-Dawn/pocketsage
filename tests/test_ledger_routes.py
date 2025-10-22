from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse, parse_qs

import pytest

from pocketsage import create_app
from pocketsage.extensions import session_scope
from pocketsage.models import Transaction


@pytest.fixture()
def ledger_app(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "ledger.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    app = create_app("development")
    app.config.update(TESTING=True)
    return app


@pytest.fixture()
def ledger_client(ledger_app):
    with ledger_app.test_client() as client:
        yield client


def _seed_transaction(app, **overrides) -> int:
    defaults = {
        "occurred_at": datetime(2024, 1, 1, 12, 0),
        "amount": -25.0,
        "memo": "Groceries",
        "external_id": "abc123",
        "currency": "USD",
    }
    defaults.update(overrides)

    with app.app_context():
        with session_scope() as session:
            tx = Transaction(**defaults)
            session.add(tx)
            session.flush()
            return tx.id  # type: ignore[return-value]


def test_edit_transaction_populates_form(ledger_app, ledger_client):
    tx_id = _seed_transaction(ledger_app, category_id=7)

    response = ledger_client.get(f"/ledger/{tx_id}/edit?account=checking")
    assert response.status_code == 200

    body = response.get_data(as_text=True)
    assert "Edit Ledger Entry" in body
    assert f"#{tx_id}" in body
    assert "Entry metadata" in body
    assert "Delete entry" in body
    assert "USD" in body
    assert "Groceries" in body
    assert "-25.00" in body
    assert "2024-01-01T12:00" in body
    assert "value=\"7\"" in body


def test_update_transaction_redirects_with_filters(ledger_app, ledger_client):
    tx_id = _seed_transaction(ledger_app)

    response = ledger_client.post(
        f"/ledger/{tx_id}?account=checking&category=groceries",
        data={
            "occurred_at": "2024-01-02T09:30",
            "amount": "-30.10",
            "memo": "Updated memo",
            "category_id": "5",
        },
    )
    assert response.status_code == 302

    location = response.headers["Location"]
    parsed = urlparse(location)
    assert parsed.path.endswith("/ledger/")
    query = parse_qs(parsed.query)
    assert query["account"] == ["checking"]
    assert query["category"] == ["groceries"]

    follow = ledger_client.get(location, follow_redirects=True)
    assert follow.status_code == 200
    assert b"Transaction updated successfully." in follow.data

    with ledger_app.app_context():
        with session_scope() as session:
            updated = session.get(Transaction, tx_id)
            assert updated is not None
            assert updated.memo == "Updated memo"
            assert updated.category_id == 5
            assert updated.amount == pytest.approx(-30.10)
            assert updated.occurred_at == datetime.fromisoformat("2024-01-02T09:30")


def test_update_transaction_invalid_payload_shows_error(ledger_app, ledger_client):
    tx_id = _seed_transaction(ledger_app)

    response = ledger_client.post(
        f"/ledger/{tx_id}",
        data={
            "occurred_at": "2024-01-02T09:30",
            "amount": "not-a-number",
            "memo": "Bad",  # ensure memo still provided
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "Unable to update transaction" in body
    assert "Edit Ledger Entry" in body

    with ledger_app.app_context():
        with session_scope() as session:
            unchanged = session.get(Transaction, tx_id)
            assert unchanged is not None
            assert unchanged.memo == "Groceries"
            assert unchanged.amount == pytest.approx(-25.0)

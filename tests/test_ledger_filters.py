"""Tests covering ledger filter interactions."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Iterator

import pytest
from flask import template_rendered

from pocketsage import create_app
from pocketsage.extensions import session_scope
from pocketsage.models import Category, Transaction


@pytest.fixture()
def ledger_app(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    db_path = tmp_path / "ledger.db"
    monkeypatch.setenv("POCKETSAGE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("POCKETSAGE_DATABASE_URL", f"sqlite:///{db_path}")
    app = create_app("development")
    app.testing = True
    return app


@pytest.fixture()
def ledger_client(ledger_app):
    with ledger_app.test_client() as client:
        yield client


@pytest.fixture()
def captured_templates(ledger_app) -> Iterator[list]:
    recorded: list = []

    def _record(sender, template, context, **extra):  # pragma: no cover - flask internals
        recorded.append((template, context))

    template_rendered.connect(_record, ledger_app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(_record, ledger_app)


@pytest.fixture()
def sample_ledger_data(ledger_app):
    with ledger_app.app_context():
        with session_scope() as session:
            income = Category(name="Salary", slug="salary", category_type="income")
            expense = Category(name="Coffee", slug="coffee", category_type="expense")
            session.add(income)
            session.add(expense)
            session.flush()

            transactions = [
                Transaction(
                    occurred_at=datetime(2024, 1, 5, 8, 30),
                    amount=1500.00,
                    memo="January salary",
                    category_id=income.id,
                ),
                Transaction(
                    occurred_at=datetime(2024, 1, 6, 9, 15),
                    amount=-5.75,
                    memo="Morning Coffee",
                    category_id=expense.id,
                ),
                Transaction(
                    occurred_at=datetime(2024, 2, 1, 12, 0),
                    amount=-42.10,
                    memo="Groceries",
                    category_id=expense.id,
                ),
            ]
            session.add_all(transactions)
            session.flush()

            return {
                "expense_id": expense.id,
                "transaction_count": len(transactions),
            }


def test_ledger_filters_apply_query_parameters(
    ledger_client, captured_templates, sample_ledger_data
):
    expense_id = sample_ledger_data["expense_id"]
    response = ledger_client.get(
        f"/ledger/?start_date=2024-01-06&end_date=2024-01-06&category={expense_id}&search=coffee"
    )

    assert response.status_code == 200
    assert captured_templates
    _, context = captured_templates[-1]

    state = context["filter_state"]
    assert state["start_date"] == "2024-01-06"
    assert state["end_date"] == "2024-01-06"
    assert state["category"] == str(expense_id)
    assert state["search"] == "coffee"

    transactions = context["transactions"]
    assert len(transactions) == 1
    assert transactions[0].memo == "Morning Coffee"

    body = response.get_data(as_text=True)
    assert "value=\"2024-01-06\"" in body
    assert f'<option value="{expense_id}" selected' in body
    assert 'value="coffee"' in body


def test_invalid_filters_reset_state(ledger_client, captured_templates, sample_ledger_data):
    response = ledger_client.get("/ledger/?start_date=oops&category=not-a-number&search= ")

    assert response.status_code == 200
    _, context = captured_templates[-1]

    state = context["filter_state"]
    assert state["start_date"] == ""
    assert state["end_date"] == ""
    assert state["category"] == ""
    assert state["search"] == ""

    filters = context["filters"]
    assert filters == {}

    transactions = context["transactions"]
    assert len(transactions) == sample_ledger_data["transaction_count"]


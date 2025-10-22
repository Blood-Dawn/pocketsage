"""Ledger routes."""

from __future__ import annotations

from datetime import date
from typing import Any, Tuple

from flask import flash, g, redirect, render_template, request, url_for

from . import bp
from .repository import SqlModelLedgerRepository


def _parse_date(value: str | None) -> date | None:
    """Attempt to parse ISO-8601 date strings."""

    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _extract_filters(args) -> Tuple[dict[str, Any], dict[str, str]]:
    """Convert request arguments into repository filters and form state."""

    form_state: dict[str, str] = {
        "start_date": args.get("start_date", ""),
        "end_date": args.get("end_date", ""),
        "category": args.get("category", ""),
        "search": args.get("search", ""),
    }

    filters: dict[str, Any] = {}

    start_date = _parse_date(form_state["start_date"] or None)
    if start_date is not None:
        filters["start_date"] = start_date
        form_state["start_date"] = start_date.isoformat()
    else:
        form_state["start_date"] = ""

    end_date = _parse_date(form_state["end_date"] or None)
    if end_date is not None:
        filters["end_date"] = end_date
        form_state["end_date"] = end_date.isoformat()
    else:
        form_state["end_date"] = ""

    category_raw = (form_state["category"] or "").strip()
    if category_raw:
        try:
            filters["category_id"] = int(category_raw)
            form_state["category"] = str(filters["category_id"])
        except ValueError:
            form_state["category"] = ""
    else:
        form_state["category"] = ""

    search_raw = (form_state["search"] or "").strip()
    if search_raw:
        filters["search"] = search_raw
        form_state["search"] = search_raw
    else:
        form_state["search"] = ""

    return filters, form_state


@bp.get("/")
def list_transactions():
    """Display ledger transactions with filters and rollups."""

    filters, form_state = _extract_filters(request.args)
    repo = SqlModelLedgerRepository(g.sqlmodel_session)
    transactions = repo.list_transactions(filters=filters)
    categories = repo.list_categories()

    # TODO(@ledger-squad): wire pagination + rollup summary calculations.
    return render_template(
        "ledger/index.html",
        filters=filters,
        filter_state=form_state,
        transactions=transactions,
        categories=categories,
    )


@bp.get("/new")
def new_transaction():
    """Render form for creating a transaction."""

    # TODO(@ledger-squad): supply LedgerEntryForm with defaults (see forms.py).
    return render_template("ledger/form.html")


@bp.post("/")
def create_transaction():
    """Persist a new transaction from submitted form data."""

    # TODO(@ledger-squad): validate form payloads and perform repository insert.
    flash("Ledger transaction creation not yet implemented", "warning")
    return redirect(url_for("ledger.list_transactions"))


@bp.get("/<int:transaction_id>/edit")
def edit_transaction(transaction_id: int):
    """Render edit form for a specific transaction."""

    # TODO(@ledger-squad): fetch transaction + populate form state from repository.
    return render_template("ledger/form.html", transaction_id=transaction_id)


@bp.post("/<int:transaction_id>")
def update_transaction(transaction_id: int):
    """Handle update submissions for an existing transaction."""

    # TODO(@ledger-squad): apply optimistic locking + repository update.
    flash("Ledger transaction update not yet implemented", "warning")
    return redirect(url_for("ledger.list_transactions"))

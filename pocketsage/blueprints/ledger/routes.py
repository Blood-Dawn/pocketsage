"""Ledger routes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import flash, redirect, render_template, request, url_for

from ...extensions import session_scope
from . import bp
from .repository import SqlModelLedgerRepository

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 100


def _clean_filters(args: Mapping[str, str]) -> dict[str, str]:
    """Normalize query-string filters for repository consumption."""

    skip_keys = {"page", "per_page"}
    return {k: v for k, v in args.items() if k not in skip_keys and v}


def _parse_positive_int(value: str | None, *, default: int, upper: int | None = None) -> int:
    """Parse integer query params while enforcing sane bounds."""

    try:
        parsed = int(value) if value is not None else default
    except (TypeError, ValueError):
        return default

    if parsed < 1:
        parsed = default

    if upper is not None:
        parsed = min(parsed, upper)

    return parsed


@bp.get("/")
def list_transactions():
    """Display ledger transactions with filters and rollups."""

    filters = _clean_filters(request.args)
    page = _parse_positive_int(request.args.get("page"), default=1)
    per_page = _parse_positive_int(
        request.args.get("per_page"), default=DEFAULT_PAGE_SIZE, upper=MAX_PAGE_SIZE
    )

    with session_scope() as session:
        repo = SqlModelLedgerRepository(session)
        result = repo.list_transactions(filters=filters, page=page, per_page=per_page)

    pagination = result.pagination

    def _page_url(target_page: int) -> str:
        params: dict[str, Any] = {**filters, "page": target_page, "per_page": pagination.per_page}
        return url_for("ledger.list_transactions", **params)

    prev_url = _page_url(pagination.page - 1) if pagination.has_prev else None
    next_url = _page_url(pagination.page + 1) if pagination.has_next else None

    return render_template(
        "ledger/index.html",
        filters=filters,
        transactions=result.transactions,
        summary=result.summary,
        pagination=pagination,
        prev_url=prev_url,
        next_url=next_url,
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

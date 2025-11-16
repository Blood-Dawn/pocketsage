"""Ledger routes."""

from __future__ import annotations

from math import ceil

from flask import flash, g, redirect, render_template, request, url_for

from flask import flash, g, redirect, render_template, request, url_for

from ...extensions import session_scope
from . import bp
from .repository import SQLModelLedgerRepository


DEFAULT_PER_PAGE = 25
PER_PAGE_CHOICES = (10, 25, 50, 100)


@bp.get("/")
def list_transactions():
    """Display ledger transactions with filters, pagination, and rollups."""

    session = g.get("sqlmodel_session")
    if session is None:
        raise RuntimeError("Database session not initialized for request")

    requested_page = _coerce_int(request.args.get("page"), default=1)
    requested_per_page = _coerce_int(
        request.args.get("per_page"), default=DEFAULT_PER_PAGE, minimum=1, maximum=100
    )

    filters = {
        key: value
        for key, value in request.args.items()
        if key not in {"page", "per_page"} and value
    }

    repository = SQLModelLedgerRepository(session=session)
    transactions, total = repository.list_transactions(
        filters=filters, page=requested_page, per_page=requested_per_page
    )

    total_pages = max(ceil(total / requested_per_page), 1) if total else 1
    current_page = min(max(requested_page, 1), total_pages)

    if total and current_page != requested_page:
        transactions, _ = repository.list_transactions(
            filters=filters, page=current_page, per_page=requested_per_page
        )

    start_index = (current_page - 1) * requested_per_page
    page_start = start_index + 1 if total else 0
    page_end = min(start_index + len(transactions), total) if total else 0

    pagination = {
        "page": current_page,
        "per_page": requested_per_page,
        "total": total,
        "pages": total_pages,
        "has_prev": current_page > 1,
        "has_next": current_page < total_pages,
        "start": page_start,
        "end": page_end,
        "window": _pagination_window(current_page, total_pages),
    }

    def page_url(target_page: int) -> str:
        params = dict(filters)
        params["page"] = target_page
        params["per_page"] = requested_per_page
        return url_for("ledger.list_transactions", **params)

    context = {
        "filters": filters,
        "transactions": transactions,
        "pagination": pagination,
        "page_url": page_url,
        "per_page_options": _per_page_options(requested_per_page),
    }

    return render_template("ledger/index.html", **context)


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


def _coerce_int(
    value: str | None,
    *,
    default: int,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    """Convert ``value`` to an ``int`` within optional bounds."""

    try:
        result = int(value) if value is not None else default
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(result, minimum)
    if maximum is not None:
        result = min(result, maximum)
    return result


def _pagination_window(current_page: int, total_pages: int, width: int = 2) -> list[int | None]:
    """Return a condensed pagination range with ellipses."""

    if total_pages <= (width * 2 + 5):
        return list(range(1, total_pages + 1))

    window_start = max(current_page - width, 1)
    window_end = min(current_page + width, total_pages)

    window: list[int | None] = [1]

    if window_start > 2:
        window.append(None)

    window.extend(range(window_start, window_end + 1))

    if window_end < total_pages - 1:
        window.append(None)

    if total_pages not in window:
        window.append(total_pages)

    return window


def _per_page_options(selected: int) -> tuple[int, ...]:
    """Return a sorted tuple of available page sizes including ``selected``."""

    options = list(PER_PAGE_CHOICES)
    if selected not in options:
        options.append(selected)
    return tuple(sorted(dict.fromkeys(options)))

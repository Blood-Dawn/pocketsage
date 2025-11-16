"""Ledger routes."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import NotFound

from ...extensions import session_scope
from ...models.transaction import Transaction
from . import bp
from .forms import LedgerEntryForm


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

    filters = request.args.to_dict(flat=True)
    form = LedgerEntryForm()
    return render_template(
        "ledger/form.html",
        form=form,
        form_values=_form_values(form),
        filters=filters,
        form_action=url_for("ledger.create_transaction"),
        list_url=url_for("ledger.list_transactions", **filters),
        metadata=None,
        is_edit=False,
    )


@bp.post("/")
def create_transaction():
    """Persist a new transaction from submitted form data."""

    form = LedgerEntryForm.from_mapping(request.form)
    if not form.validate():
        return render_template("ledger/form.html", form=form), 400

    # TODO(@ledger-squad): perform repository insert when backend is ready.
    flash("Ledger transaction creation not yet implemented", "warning")
    return redirect(url_for("ledger.list_transactions"))


@bp.get("/<int:transaction_id>/edit")
def edit_transaction(transaction_id: int):
    """Render edit form for a specific transaction."""

    filters = request.args.to_dict(flat=True)
    with session_scope() as session:
        transaction = session.get(Transaction, transaction_id)
        if transaction is None:
            raise NotFound(f"Transaction {transaction_id} was not found")

        form = LedgerEntryForm(
            occurred_at=transaction.occurred_at,
            amount=transaction.amount,
            memo=transaction.memo or "",
            category_id=transaction.category_id,
        )

        account_label: str | None = None
        if getattr(transaction, "account", None) is not None:
            account_name = getattr(transaction.account, "name", None)
            if account_name:
                account_label = account_name
        if account_label is None and transaction.account_id is not None:
            account_label = f"Account #{transaction.account_id}"

        metadata: dict[str, Any] = {
            "id": transaction.id,
            "occurred_at": transaction.occurred_at.isoformat() if transaction.occurred_at else None,
            "amount": f"{transaction.amount:,.2f}" if transaction.amount is not None else None,
            "currency": transaction.currency,
            "external_id": transaction.external_id,
            "account": account_label,
            "memo": transaction.memo or "",
            "category_id": transaction.category_id,
        }

        created_at = getattr(transaction, "created_at", None)
        if created_at is not None:
            metadata["created_at"] = created_at.isoformat()
        updated_at = getattr(transaction, "updated_at", None)
        if updated_at is not None:
            metadata["updated_at"] = updated_at.isoformat()

    return render_template(
        "ledger/form.html",
        form=form,
        form_values=_form_values(form),
        filters=filters,
        form_action=url_for("ledger.update_transaction", transaction_id=transaction_id, **filters),
        list_url=url_for("ledger.list_transactions", **filters),
        metadata=metadata,
        is_edit=True,
        transaction_id=transaction_id,
    )


@bp.post("/<int:transaction_id>")
def update_transaction(transaction_id: int):
    """Handle update submissions for an existing transaction."""

    filters = request.args.to_dict(flat=True)
    redirect_to_edit = lambda: redirect(
        url_for("ledger.edit_transaction", transaction_id=transaction_id, **filters)
    )

    occurred_raw = request.form.get("occurred_at")
    amount_raw = request.form.get("amount")
    if not occurred_raw or amount_raw in (None, ""):
        flash("Unable to update transaction; please check the provided details.", "danger")
        return redirect_to_edit()

    try:
        occurred_at = datetime.fromisoformat(occurred_raw)
        amount = float(amount_raw)
    except ValueError:
        flash("Unable to update transaction; please check the provided details.", "danger")
        return redirect_to_edit()

    memo = (request.form.get("memo") or "").strip()
    category_raw = request.form.get("category_id")
    category_id: int | None = None
    if category_raw not in (None, ""):
        try:
            category_id = int(category_raw)
        except ValueError:
            flash("Unable to update transaction; please check the provided details.", "danger")
            return redirect_to_edit()

    try:
        with session_scope() as session:
            transaction = session.get(Transaction, transaction_id)
            if transaction is None:
                flash("Transaction could not be found.", "warning")
                return redirect(url_for("ledger.list_transactions", **filters))

            transaction.occurred_at = occurred_at
            transaction.amount = amount
            transaction.memo = memo
            transaction.category_id = category_id
            session.add(transaction)
    except Exception:  # pragma: no cover - surfaced via flash for user feedback
        current_app.logger.exception(
            "Failed to update ledger transaction %s", transaction_id
        )
        flash("An unexpected error occurred while updating the transaction.", "danger")
        return redirect_to_edit()

    flash("Transaction updated successfully.", "success")
    return redirect(url_for("ledger.list_transactions", **filters))


def _form_values(form: LedgerEntryForm) -> dict[str, str]:
    """Convert a LedgerEntryForm into HTML-friendly string values."""

    occurred_value = ""
    if form.occurred_at is not None:
        if isinstance(form.occurred_at, datetime):
            occurred_value = form.occurred_at.strftime("%Y-%m-%dT%H:%M")
        else:
            occurred_value = str(form.occurred_at)

    amount_value = ""
    if form.amount is not None:
        amount_value = f"{form.amount:.2f}"

    category_value = ""
    if form.category_id is not None:
        category_value = str(form.category_id)

    return {
        "occurred_at": occurred_value,
        "amount": amount_value,
        "memo": form.memo,
        "category_id": category_value,
    }

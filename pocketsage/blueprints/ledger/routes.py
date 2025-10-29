"""Ledger routes."""

from __future__ import annotations

from datetime import datetime

from flask import flash, redirect, render_template, request, url_for

from . import bp
from .forms import LedgerEntryForm


@bp.get("/")
def list_transactions():
    """Display ledger transactions with filters and rollups."""

    # TODO(@ledger-squad): wire repository filtering + pagination + rollup summary.
    return render_template("ledger/index.html", filters=request.args)


@bp.get("/new")
def new_transaction():
    """Render form for creating a transaction."""

    form = LedgerEntryForm(
        occurred_at=datetime.now().replace(second=0, microsecond=0),
        amount=None,
        memo="",
        category_id=None,
    )
    return render_template("ledger/form.html", form=form)


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

"""Ledger routes."""

from __future__ import annotations

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

    form = LedgerEntryForm()
    return render_template("ledger/form.html", form=form)


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

    # TODO(@ledger-squad): fetch transaction + populate form state from repository.
    form = LedgerEntryForm()
    return render_template("ledger/form.html", transaction_id=transaction_id, form=form)


@bp.post("/<int:transaction_id>")
def update_transaction(transaction_id: int):
    """Handle update submissions for an existing transaction."""

    form = LedgerEntryForm.from_mapping(request.form)
    if not form.validate():
        return render_template(
            "ledger/form.html", transaction_id=transaction_id, form=form
        ), 400

    # TODO(@ledger-squad): apply optimistic locking + repository update.
    flash("Ledger transaction update not yet implemented", "warning")
    return redirect(url_for("ledger.list_transactions"))

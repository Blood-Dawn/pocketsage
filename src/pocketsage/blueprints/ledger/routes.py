"""Ledger routes."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Iterable, Mapping

from flask import current_app, flash, redirect, render_template, request, url_for
from werkzeug.exceptions import NotFound

from ...extensions import session_scope
from ...models.transaction import Transaction
from . import bp
from .forms import LedgerEntryForm


@dataclass(frozen=True)
class DemoTransaction:
    """Lightweight structure used to populate the ledger prototype."""

    occurred_at: datetime
    amount: float
    memo: str
    category: str


# Seed the prototype ledger with representative inflow and outflow data. The
# sample spans two months so that the UI can surface a meaningful trend
# indicator when comparing periods.
_DEMO_TRANSACTIONS: tuple[DemoTransaction, ...] = (
    DemoTransaction(
        occurred_at=datetime(2024, 3, 1),
        amount=4200.0,
        memo="Salary · Acme Corp",
        category="Income",
    ),
    DemoTransaction(
        occurred_at=datetime(2024, 3, 2),
        amount=-125.34,
        memo="Groceries · Fresh Market",
        category="Household",
    ),
    DemoTransaction(
        occurred_at=datetime(2024, 3, 5),
        amount=-89.5,
        memo="Utilities · City Power",
        category="Utilities",
    ),
    DemoTransaction(
        occurred_at=datetime(2024, 3, 12),
        amount=-230.0,
        memo="Dining · Weekend outings",
        category="Dining",
    ),
    DemoTransaction(
        occurred_at=datetime(2024, 3, 18),
        amount=150.0,
        memo="Freelance · Design gig",
        category="Income",
    ),
    DemoTransaction(
        occurred_at=datetime(2024, 2, 29),
        amount=4100.0,
        memo="Salary · Acme Corp",
        category="Income",
    ),
    DemoTransaction(
        occurred_at=datetime(2024, 2, 21),
        amount=-118.75,
        memo="Groceries · Fresh Market",
        category="Household",
    ),
    DemoTransaction(
        occurred_at=datetime(2024, 2, 8),
        amount=-92.1,
        memo="Utilities · City Power",
        category="Utilities",
    ),
)


def _period_key(value: datetime) -> str:
    return value.strftime("%Y-%m")


def _period_label(key: str | None) -> str | None:
    if not key:
        return None
    period_start = datetime.strptime(f"{key}-01", "%Y-%m-%d")
    return period_start.strftime("%B %Y")


def _format_currency(value: float, *, absolute: bool = False) -> str:
    display_value = abs(value) if absolute else value
    prefix = "-" if (not absolute and display_value < 0) else ""
    return f"{prefix}$ {abs(display_value):,.2f}"


def _summarize_transactions(
    transactions: Iterable[DemoTransaction],
) -> tuple[list[Mapping[str, object]], str | None, str | None]:
    """Return rollup metrics and human-readable period labels."""

    monthly_totals: dict[str, dict[str, float]] = defaultdict(
        lambda: {"income": 0.0, "expenses": 0.0, "balance": 0.0}
    )

    for txn in transactions:
        period = _period_key(txn.occurred_at)
        bucket = monthly_totals[period]
        if txn.amount >= 0:
            bucket["income"] += txn.amount
        else:
            bucket["expenses"] += abs(txn.amount)
        bucket["balance"] += txn.amount

    if not monthly_totals:
        return [], None, None

    periods = sorted(monthly_totals.keys())
    current_period_key = periods[-1]
    previous_period_key = periods[-2] if len(periods) > 1 else None

    current_label = _period_label(current_period_key)
    previous_label = _period_label(previous_period_key)

    metric_definitions = (
        ("income", "Income", True),
        ("expenses", "Expenses", True),
        ("balance", "Net balance", False),
    )

    rollups: list[Mapping[str, object]] = []
    for key, label, absolute in metric_definitions:
        current_value = monthly_totals[current_period_key][key]
        has_comparison = previous_period_key is not None
        previous_value = monthly_totals[previous_period_key][key] if has_comparison else 0.0
        change = current_value - previous_value if has_comparison else 0.0

        direction = "flat"
        if has_comparison:
            if change > 1e-2:
                direction = "up"
            elif change < -1e-2:
                direction = "down"
        elif current_value > 0:
            direction = "up"

        percent_change: float | None = None
        if has_comparison and abs(previous_value) > 1e-9:
            percent_change = (change / previous_value) * 100

        if not has_comparison:
            trend_value = "First period"
            trend_caption = "No prior period"
            trend_sr_text = f"{label} for {current_label} with no prior comparison."
        elif percent_change is None and abs(change) > 1e-2:
            trend_value = "New this period"
            trend_caption = f"Previously 0 in {previous_label}"
            trend_sr_text = f"{label} introduced this period after no activity in {previous_label}."
        else:
            magnitude = abs(percent_change) if percent_change is not None else 0.0
            if direction == "flat":
                trend_value = "No change"
                trend_sr_text = f"{label} unchanged compared to {previous_label}."
            elif direction == "up":
                trend_value = f"Up {magnitude:.1f}%"
                trend_sr_text = (
                    f"{label} increased {magnitude:.1f} percent compared to {previous_label}."
                )
            else:
                trend_value = f"Down {magnitude:.1f}%"
                trend_sr_text = (
                    f"{label} decreased {magnitude:.1f} percent compared to {previous_label}."
                )
            trend_caption = f"vs {previous_label}" if previous_label else ""

        rollups.append(
            {
                "key": key,
                "label": label,
                "formatted_amount": _format_currency(current_value, absolute=absolute),
                "direction": direction,
                "trend_value": trend_value,
                "trend_caption": trend_caption,
                "trend_sr_text": trend_sr_text,
            }
        )

    return rollups, current_label, previous_label


@bp.get("/")
def list_transactions():
    """Display ledger transactions with filters, pagination, and rollups."""

    rollups, current_period_label, previous_period_label = _summarize_transactions(
        _DEMO_TRANSACTIONS
    )

    return render_template(
        "ledger/index.html",
        filters=request.args,
        rollups=rollups,
        current_period_label=current_period_label,
        previous_period_label=previous_period_label,
    )


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

    def redirect_to_edit():
        return redirect(
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
        current_app.logger.exception("Failed to update ledger transaction %s", transaction_id)
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

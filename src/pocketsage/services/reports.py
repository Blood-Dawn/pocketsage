"""Reporting utilities for PocketSage."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol

import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from ..models.transaction import Transaction


class ReportRenderer(Protocol):
    """Protocol describing renderer behavior."""

    def render(self, figure: Figure, *, output_path: Path) -> None:  # pragma: no cover - interface
        ...


def build_spending_chart(*, transactions: Iterable[Transaction]) -> Figure:
    """Create a matplotlib donut chart representing spending by category.

    Transactions with negative amounts are considered expenses and aggregated by category_id.
    """

    # Aggregate by category_id
    totals: dict = {}
    for tx in transactions:
        cid = getattr(tx, "category_id", "uncategorized") or "uncategorized"
        amt = float(getattr(tx, "amount", 0) or 0)
        # Only consider outflows
        if amt >= 0:
            continue
        totals[cid] = totals.get(cid, 0) + abs(amt)

    labels = [str(k) for k in totals.keys()]
    sizes = [v for v in totals.values()]

    fig, ax = plt.subplots(figsize=(6, 4))
    if sizes:
        wedges, texts = ax.pie(sizes, labels=labels, wedgeprops=dict(width=0.4), startangle=90)
        ax.axis("equal")
        ax.set_title("Spending by Category")
    else:
        ax.text(0.5, 0.5, "No expense data", ha="center", va="center")
        ax.axis("off")

    return fig


def export_transactions_csv(*, transactions: Iterable[Transaction], output_path: Path) -> None:
    """Write transaction data to CSV at the desired location."""

    from .export_csv import export_transactions_csv as _export

    _export(transactions=transactions, output_path=output_path)


def export_spending_png(
    *,
    transactions: Iterable[Transaction],
    output_path: Path,
    renderer: ReportRenderer | None = None,
) -> Path:
    """Render spending chart to PNG and return the path."""

    fig = build_spending_chart(transactions=transactions)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if renderer is not None:
        renderer.render(fig, output_path=output_path)
    else:
        fig.savefig(output_path, bbox_inches="tight")
    plt.close(fig)
    return output_path

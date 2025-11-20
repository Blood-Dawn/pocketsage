"""Chart helpers for Flet views."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pocketsage.models.portfolio import Holding

from pocketsage.models.transaction import Transaction
from pocketsage.services.reports import build_spending_chart


def spending_chart_png(transactions: Iterable[Transaction]) -> Path:
    """Render spending donut using existing reports helper and return PNG path."""
    fig = build_spending_chart(transactions=transactions)
    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight")
        path = Path(tmp.name)
    plt.close(fig)
    return path


def cashflow_trend_png(transactions: Iterable[Transaction], months: int = 6) -> Path:
    """Render a simple cashflow line chart for the last ``months`` months."""
    today = date.today()
    month_keys: list[tuple[int, int]] = []
    for offset in range(months - 1, -1, -1):
        month = (today.month - offset - 1) % 12 + 1
        year = today.year + ((today.month - offset - 1) // 12)
        month_keys.append((year, month))

    totals = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for tx in transactions:
        dt = getattr(tx, "occurred_at", None)
        if dt is None:
            continue
        key = (dt.year, dt.month)
        if key not in totals:
            continue
        amt = float(getattr(tx, "amount", 0.0) or 0.0)
        if amt >= 0:
            totals[key]["income"] += amt
        else:
            totals[key]["expense"] += abs(amt)

    income = [totals[key]["income"] for key in month_keys]
    expense = [totals[key]["expense"] for key in month_keys]
    labels = [f"{y}-{m:02d}" for y, m in month_keys]

    x_positions = list(range(len(labels)))

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(x_positions, income, marker="o", label="Income")
    ax.plot(x_positions, expense, marker="o", label="Expenses")
    ax.fill_between(x_positions, income, expense, color="#e0e7ff", alpha=0.4)
    ax.set_title("Cashflow by Month")
    ax.set_ylabel("Amount")
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.legend()
    plt.tight_layout()

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight")
        path = Path(tmp.name)
    plt.close(fig)
    return path


def allocation_chart_png(holdings: Iterable[Holding]) -> Path:
    """Render allocation donut chart for holdings."""
    totals = defaultdict(float)
    for h in holdings:
        value = float(getattr(h, "quantity", 0.0) or 0.0) * float(getattr(h, "avg_price", 0.0) or 0.0)
        if value <= 0:
            continue
        key = getattr(h, "symbol", "Unknown")
        totals[key] += value

    labels = list(totals.keys())
    sizes = list(totals.values())
    fig, ax = plt.subplots(figsize=(5, 4))
    if sizes:
        wedges, _ = ax.pie(sizes, labels=labels, wedgeprops=dict(width=0.4), startangle=90)
        ax.axis("equal")
        ax.set_title("Allocation")
    else:
        ax.text(0.5, 0.5, "No holdings", ha="center", va="center")
        ax.axis("off")

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight")
        path = Path(tmp.name)
    plt.close(fig)
    return path

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


def spending_chart_png(
    transactions: Iterable[Transaction], *, category_lookup: dict[int, str] | None = None
) -> Path:
    """Render spending donut using existing reports helper and return PNG path."""
    txs = list(transactions)
    if not txs:
        fig, ax = plt.subplots(figsize=(4, 3))
        ax.text(0.5, 0.5, "No spending data", ha="center", va="center")
        ax.axis("off")
        with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, bbox_inches="tight")
            path = Path(tmp.name)
        plt.close(fig)
        return path
    fig = build_spending_chart(transactions=transactions, category_lookup=category_lookup)
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
        price = float(getattr(h, "market_price", 0.0) or 0.0)
        if price <= 0:
            price = float(getattr(h, "avg_price", 0.0) or 0.0)
        value = float(getattr(h, "quantity", 0.0) or 0.0) * price
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


def debt_payoff_chart_png(schedule: Iterable[dict]) -> Path:
    """Render a simple line chart of total remaining debt over time."""

    timeline: list[str] = []
    totals: list[float] = []
    for idx, entry in enumerate(schedule):
        payments = entry.get("payments", {}) if isinstance(entry, dict) else {}
        remaining = 0.0
        for payment in payments.values():
            try:
                remaining += float(payment.get("remaining_balance", 0.0) or 0.0)
            except Exception:
                continue
        timeline.append(str(entry.get("date", f"M{idx+1}")))
        totals.append(remaining)

    fig, ax = plt.subplots(figsize=(6, 4))
    if totals:
        x_vals = list(range(len(totals)))
        ax.plot(x_vals, totals, marker="o", color="#4F46E5")
        ax.fill_between(x_vals, totals, color="#E0E7FF", alpha=0.5)
        ax.set_xticks(x_vals[:: max(1, len(x_vals) // 8)])
        labels = timeline[:: max(1, len(timeline) // 8)] or timeline
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title("Debt Payoff Projection")
        ax.set_ylabel("Remaining balance")
    else:
        ax.text(0.5, 0.5, "No payoff schedule", ha="center", va="center")
        ax.axis("off")

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight")
        path = Path(tmp.name)
    plt.close(fig)
    return path


def category_trend_png(
    transactions: Iterable[Transaction],
    *,
    category_lookup: dict[int, str] | None = None,
    months: int = 6,
) -> Path:
    """Render stacked expenses by category over the last N months."""

    from datetime import datetime

    today = date.today()
    month_keys: list[tuple[int, int]] = []
    for offset in range(months - 1, -1, -1):
        month = (today.month - offset - 1) % 12 + 1
        year = today.year + ((today.month - offset - 1) // 12)
        month_keys.append((year, month))

    totals: dict[str, list[float]] = {}
    labels = [f"{y}-{m:02d}" for y, m in month_keys]

    def label_for_category(cid: int | None) -> str:
        if cid is None:
            return "Uncategorized"
        if category_lookup and cid in category_lookup:
            return category_lookup[cid]
        return f"Category {cid}"

    idx_lookup = {key: i for i, key in enumerate(month_keys)}
    for tx in transactions:
        dt = getattr(tx, "occurred_at", None)
        amt = float(getattr(tx, "amount", 0.0) or 0.0)
        if dt is None or amt >= 0:
            continue
        key = (dt.year, dt.month)
        if key not in idx_lookup:
            continue
        cat_label = label_for_category(getattr(tx, "category_id", None))
        totals.setdefault(cat_label, [0.0] * len(month_keys))
        totals[cat_label][idx_lookup[key]] += abs(amt)

    fig, ax = plt.subplots(figsize=(7, 4))
    bottom = [0.0] * len(month_keys)
    for cat, values in totals.items():
        ax.bar(labels, values, bottom=bottom, label=cat)
        bottom = [b + v for b, v in zip(bottom, values)]
    ax.set_title("Expense trend by category")
    ax.set_ylabel("Amount")
    ax.set_xticklabels(labels, rotation=45, ha="right")
    if totals:
        ax.legend(bbox_to_anchor=(1.05, 1), loc="upper left", fontsize="x-small")
    else:
        ax.text(0.5, 0.5, "No expense data", ha="center", va="center")
    plt.tight_layout()

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight")
        path = Path(tmp.name)
    plt.close(fig)
    return path


def cashflow_by_account_png(
    transactions: Iterable[Transaction], account_lookup: dict[int, str] | None = None
) -> Path:
    """Render bar chart of net cashflow by account."""

    totals: dict[str, float] = defaultdict(float)

    def label_for_account(aid: int | None) -> str:
        if aid is None:
            return "Unassigned"
        if account_lookup and aid in account_lookup:
            return account_lookup[aid]
        return f"Account {aid}"

    for tx in transactions:
        aid = getattr(tx, "account_id", None)
        amt = float(getattr(tx, "amount", 0.0) or 0.0)
        key = label_for_account(aid)
        totals[key] += amt

    labels = list(totals.keys())
    values = [totals[k] for k in labels]

    fig, ax = plt.subplots(figsize=(6, 4))
    colors = ["#10B981" if v >= 0 else "#EF4444" for v in values]
    ax.bar(labels, values, color=colors)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_title("Cashflow by account")
    ax.set_ylabel("Net amount")
    ax.set_xticklabels(labels, rotation=45, ha="right")
    plt.tight_layout()

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight")
        path = Path(tmp.name)
    plt.close(fig)
    return path

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
import matplotlib.ticker as mticker

from pocketsage.models.portfolio import Holding
from pocketsage.models.transaction import Transaction
from pocketsage.services.reports import build_spending_chart


def spending_chart_png(
    transactions: Iterable[Transaction], *, category_lookup: dict[int, str] | None = None
) -> Path:
    """Render spending donut using existing reports helper and return PNG path."""
    txs = list(transactions)
    if not txs:
        fig, ax = plt.subplots(figsize=(6, 5))
        ax.text(0.5, 0.5, "No spending data", ha="center", va="center", fontsize=14, color="#666")
        ax.axis("off")
        with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
            path = Path(tmp.name)
        plt.close(fig)
        return path
    fig = build_spending_chart(transactions=transactions, category_lookup=category_lookup)
    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
        path = Path(tmp.name)
    plt.close(fig)
    return path


def cashflow_trend_png(transactions: Iterable[Transaction], months: int = 6) -> Path:
    """Render an enhanced cashflow line chart for the last ``months`` months."""

    txs = list(transactions)

    # Show placeholder if no transactions
    if not txs:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, "No transaction data yet\nAdd transactions to see your cashflow",
                ha="center", va="center", fontsize=12, color="#999")
        ax.axis("off")
        with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
            path = Path(tmp.name)
        plt.close(fig)
        return path

    today = date.today()
    month_keys: list[tuple[int, int]] = []
    for offset in range(months - 1, -1, -1):
        month = (today.month - offset - 1) % 12 + 1
        year = today.year + ((today.month - offset - 1) // 12)
        month_keys.append((year, month))

    totals = defaultdict(lambda: {"income": 0.0, "expense": 0.0})
    for tx in txs:
        dt = getattr(tx, "occurred_at", None)
        if dt is None:
            continue
        key = (dt.year, dt.month)
        if key not in month_keys:
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

    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot lines with better styling
    ax.plot(x_positions, income, marker="o", linewidth=2.5, markersize=8,
            label="Income", color="#22C55E")
    ax.plot(x_positions, expense, marker="s", linewidth=2.5, markersize=8,
            label="Expenses", color="#EF4444")

    # Fill between for visual clarity
    ax.fill_between(x_positions, income, expense,
                    where=[i >= e for i, e in zip(income, expense)],
                    color="#DCFCE7", alpha=0.4, label="Surplus")
    ax.fill_between(x_positions, income, expense,
                    where=[i < e for i, e in zip(income, expense)],
                    color="#FEE2E2", alpha=0.4, label="Deficit")

    # Add value labels on data points
    for i, (inc, exp) in enumerate(zip(income, expense)):
        if inc > 0:
            ax.annotate(f'${inc:,.0f}', (i, inc),
                       textcoords="offset points", xytext=(0, 10),
                       ha='center', fontsize=8, color="#22C55E", fontweight='bold')
        if exp > 0:
            ax.annotate(f'${exp:,.0f}', (i, exp),
                       textcoords="offset points", xytext=(0, -15),
                       ha='center', fontsize=8, color="#EF4444", fontweight='bold')

    # Gridlines
    ax.grid(True, linestyle='--', alpha=0.3)
    ax.set_axisbelow(True)

    # Labels and formatting
    ax.set_title("Cashflow by Month", fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel("Amount ($)", fontsize=11)
    ax.set_xlabel("Month", fontsize=11)

    # FIX: Set ticks BEFORE setting tick labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=45, ha="right")

    # Format y-axis as currency
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    # Legend
    ax.legend(loc='upper left', framealpha=0.9)

    # Summary stats in text box
    total_income = sum(income)
    total_expense = sum(expense)
    net = total_income - total_expense
    net_color = "#22C55E" if net >= 0 else "#EF4444"

    textstr = f'Total Income: ${total_income:,.0f}\nTotal Expenses: ${total_expense:,.0f}\nNet: ${net:,.0f}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.98, 0.98, textstr, transform=ax.transAxes, fontsize=9,
            verticalalignment='top', horizontalalignment='right', bbox=props)

    plt.tight_layout()

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
        path = Path(tmp.name)
    plt.close(fig)
    return path


def allocation_chart_png(holdings: Iterable[Holding]) -> Path:
    """Render enhanced allocation donut chart for holdings."""

    totals = defaultdict(float)
    grand_total = 0.0

    for h in holdings:
        price = float(getattr(h, "market_price", 0.0) or 0.0)
        if price <= 0:
            price = float(getattr(h, "avg_price", 0.0) or 0.0)
        value = float(getattr(h, "quantity", 0.0) or 0.0) * price
        if value <= 0:
            continue
        key = getattr(h, "symbol", "Unknown")
        totals[key] += value
        grand_total += value

    labels = list(totals.keys())
    sizes = list(totals.values())

    fig, ax = plt.subplots(figsize=(8, 6))

    if sizes:
        # Calculate percentages
        percentages = [(s / grand_total * 100) if grand_total > 0 else 0 for s in sizes]

        # Color palette
        cmap = plt.get_cmap("tab20")
        colors = [cmap(i / len(sizes)) for i in range(len(sizes))]

        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,
            autopct=lambda pct: f'{pct:.1f}%' if pct > 3 else '',
            wedgeprops=dict(width=0.5, edgecolor='white'),
            startangle=90,
            colors=colors,
            pctdistance=0.75,
        )

        # Center text with total
        ax.text(0, 0, f'Total\n${grand_total:,.0f}',
                ha='center', va='center', fontsize=12, fontweight='bold')

        # Legend with amounts
        legend_labels = [
            f'{label}: ${size:,.0f} ({pct:.1f}%)'
            for label, size, pct in zip(labels, sizes, percentages)
        ]
        ax.legend(
            wedges,
            legend_labels,
            title="Holdings",
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=8,
        )

        ax.axis("equal")
        ax.set_title("Portfolio Allocation", fontsize=14, fontweight='bold', pad=15)
    else:
        ax.text(0.5, 0.5, "No holdings", ha="center", va="center", fontsize=14, color="#666")
        ax.axis("off")

    plt.tight_layout()

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
        path = Path(tmp.name)
    plt.close(fig)
    return path


def debt_payoff_chart_png(schedule: Iterable[dict]) -> Path:
    """Render an enhanced debt payoff projection chart."""

    schedule_list = list(schedule)
    timeline: list[str] = []
    totals: list[float] = []

    for idx, entry in enumerate(schedule_list):
        payments = entry.get("payments", {}) if isinstance(entry, dict) else {}
        remaining = 0.0
        for payment in payments.values():
            try:
                remaining += float(payment.get("remaining_balance", 0.0) or 0.0)
            except Exception:
                continue
        timeline.append(str(entry.get("date", f"M{idx+1}")))
        totals.append(remaining)

    fig, ax = plt.subplots(figsize=(10, 6))

    if totals:
        x_vals = list(range(len(totals)))

        # Main line with gradient fill
        ax.plot(x_vals, totals, marker="o", color="#4F46E5", linewidth=2.5, markersize=6)
        ax.fill_between(x_vals, totals, color="#E0E7FF", alpha=0.5)

        # Add milestone markers
        if len(totals) > 1 and totals[0] > 0:
            initial = totals[0]

            # Mark 50% point
            half_point = initial / 2
            for i, total in enumerate(totals):
                if total <= half_point:
                    ax.axvline(x=i, color='#22C55E', linestyle='--', alpha=0.6, linewidth=1.5)
                    ax.annotate('50% Paid!', (i, total),
                               xytext=(10, 30), textcoords='offset points',
                               fontsize=9, color='#22C55E', fontweight='bold',
                               arrowprops=dict(arrowstyle='->', color='#22C55E', alpha=0.6))
                    break

            # Mark 75% point
            quarter_point = initial / 4
            for i, total in enumerate(totals):
                if total <= quarter_point:
                    ax.axvline(x=i, color='#16A34A', linestyle='--', alpha=0.6, linewidth=1.5)
                    ax.annotate('75% Paid!', (i, total),
                               xytext=(10, 20), textcoords='offset points',
                               fontsize=9, color='#16A34A', fontweight='bold')
                    break

        # Mark debt-free point
        if totals and (totals[-1] == 0 or totals[-1] < 1):
            ax.scatter([x_vals[-1]], [0], s=200, c='gold', marker='*', zorder=5, edgecolors='#F59E0B')
            ax.annotate('DEBT FREE!', (x_vals[-1], 0),
                       xytext=(0, 25), textcoords='offset points',
                       ha='center', fontsize=12, fontweight='bold', color='#16A34A')

        # Gridlines
        ax.grid(True, linestyle='--', alpha=0.3)
        ax.set_axisbelow(True)

        # Labels
        ax.set_title("Debt Payoff Projection", fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel("Remaining Balance ($)", fontsize=11)
        ax.set_xlabel("Month", fontsize=11)

        # X-axis ticks - FIX: Set ticks BEFORE labels
        tick_step = max(1, len(x_vals) // 8)
        tick_positions = x_vals[::tick_step]
        tick_labels = timeline[::tick_step] if timeline else []
        ax.set_xticks(tick_positions)
        ax.set_xticklabels(tick_labels, rotation=45, ha="right")

        # Y-axis currency format
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Stats box
        months_to_payoff = len([t for t in totals if t > 0])
        starting_debt = totals[0] if totals else 0
        textstr = f'Starting Debt: ${starting_debt:,.0f}\nMonths to Payoff: {months_to_payoff}'
        props = dict(boxstyle='round', facecolor='lavender', alpha=0.8)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)
    else:
        ax.text(0.5, 0.5, "No payoff schedule", ha="center", va="center", fontsize=14, color="#666")
        ax.axis("off")

    plt.tight_layout()

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
        path = Path(tmp.name)
    plt.close(fig)
    return path


def category_trend_png(
    transactions: Iterable[Transaction],
    *,
    category_lookup: dict[int, str] | None = None,
    months: int = 6,
) -> Path:
    """Render enhanced stacked expenses by category over the last N months."""

    txs = list(transactions)

    if not txs:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, "No transaction data", ha="center", va="center", fontsize=14, color="#666")
        ax.axis("off")
        with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
            path = Path(tmp.name)
        plt.close(fig)
        return path

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
    for tx in txs:
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

    fig, ax = plt.subplots(figsize=(10, 6))

    if totals:
        # Sort categories by total spending (descending)
        sorted_cats = sorted(totals.items(), key=lambda x: sum(x[1]), reverse=True)

        # Color palette
        cmap = plt.get_cmap("tab20")

        x_positions = list(range(len(labels)))
        bottom = [0.0] * len(month_keys)

        for i, (cat, values) in enumerate(sorted_cats):
            color = cmap(i / len(sorted_cats))
            ax.bar(x_positions, values, bottom=bottom, label=cat, color=color, edgecolor='white', linewidth=0.5)
            bottom = [b + v for b, v in zip(bottom, values)]

        # Add total labels on top of each bar
        for i, total in enumerate(bottom):
            if total > 0:
                ax.annotate(f'${total:,.0f}', (i, total),
                           textcoords="offset points", xytext=(0, 5),
                           ha='center', fontsize=8, fontweight='bold')

        # Gridlines
        ax.grid(True, linestyle='--', alpha=0.3, axis='y')
        ax.set_axisbelow(True)

        ax.set_title("Expense Trend by Category", fontsize=14, fontweight='bold', pad=15)
        ax.set_ylabel("Amount ($)", fontsize=11)
        ax.set_xlabel("Month", fontsize=11)

        # FIX: Set ticks BEFORE labels
        ax.set_xticks(x_positions)
        ax.set_xticklabels(labels, rotation=45, ha="right")

        # Y-axis currency format
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))

        # Legend
        ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8, title="Categories")

        # Summary stats
        grand_total = sum(bottom)
        avg_monthly = grand_total / len(month_keys) if month_keys else 0
        textstr = f'Total: ${grand_total:,.0f}\nAvg/Month: ${avg_monthly:,.0f}'
        props = dict(boxstyle='round', facecolor='lightyellow', alpha=0.8)
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props)
    else:
        ax.text(0.5, 0.5, "No expense data", ha="center", va="center", fontsize=14, color="#666")
        ax.axis("off")

    plt.tight_layout()

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
        path = Path(tmp.name)
    plt.close(fig)
    return path


def cashflow_by_account_png(
    transactions: Iterable[Transaction], account_lookup: dict[int, str] | None = None
) -> Path:
    """Render enhanced bar chart of net cashflow by account."""

    txs = list(transactions)

    if not txs:
        fig, ax = plt.subplots(figsize=(8, 5))
        ax.text(0.5, 0.5, "No transaction data", ha="center", va="center", fontsize=14, color="#666")
        ax.axis("off")
        with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
            fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
            path = Path(tmp.name)
        plt.close(fig)
        return path

    totals: dict[str, float] = defaultdict(float)

    def label_for_account(aid: int | None) -> str:
        if aid is None:
            return "Unassigned"
        if account_lookup and aid in account_lookup:
            return account_lookup[aid]
        return f"Account {aid}"

    for tx in txs:
        aid = getattr(tx, "account_id", None)
        amt = float(getattr(tx, "amount", 0.0) or 0.0)
        key = label_for_account(aid)
        totals[key] += amt

    # Sort by absolute value
    sorted_items = sorted(totals.items(), key=lambda x: abs(x[1]), reverse=True)
    labels = [item[0] for item in sorted_items]
    values = [item[1] for item in sorted_items]

    fig, ax = plt.subplots(figsize=(10, 6))

    x_positions = list(range(len(labels)))
    colors = ["#22C55E" if v >= 0 else "#EF4444" for v in values]

    bars = ax.bar(x_positions, values, color=colors, edgecolor='white', linewidth=0.5)

    # Add value labels on bars
    for i, (bar, val) in enumerate(zip(bars, values)):
        height = bar.get_height()
        va = 'bottom' if height >= 0 else 'top'
        offset = 5 if height >= 0 else -5
        ax.annotate(f'${val:,.0f}',
                   xy=(bar.get_x() + bar.get_width() / 2, height),
                   xytext=(0, offset),
                   textcoords="offset points",
                   ha='center', va=va, fontsize=9, fontweight='bold',
                   color=colors[i])

    ax.axhline(0, color="black", linewidth=0.8)

    # Gridlines
    ax.grid(True, linestyle='--', alpha=0.3, axis='y')
    ax.set_axisbelow(True)

    ax.set_title("Net Cashflow by Account", fontsize=14, fontweight='bold', pad=15)
    ax.set_ylabel("Net Amount ($)", fontsize=11)
    ax.set_xlabel("Account", fontsize=11)

    # FIX: Set ticks BEFORE labels
    ax.set_xticks(x_positions)
    ax.set_xticklabels(labels, rotation=45, ha="right")

    # Y-axis currency format
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, p: f'${x:,.0f}'))

    # Summary
    total_net = sum(values)
    net_color = "#22C55E" if total_net >= 0 else "#EF4444"
    textstr = f'Total Net: ${total_net:,.0f}'
    props = dict(boxstyle='round', facecolor='wheat', alpha=0.8)
    ax.text(0.98, 0.98, textstr, transform=ax.transAxes, fontsize=10,
            verticalalignment='top', horizontalalignment='right', bbox=props,
            color=net_color, fontweight='bold')

    plt.tight_layout()

    with NamedTemporaryFile(delete=False, suffix=".png") as tmp:
        fig.savefig(tmp.name, bbox_inches="tight", dpi=100)
        path = Path(tmp.name)
    plt.close(fig)
    return path

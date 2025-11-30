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


def build_spending_chart(
    *,
    transactions: Iterable[Transaction],
    category_lookup: dict[object, str] | None = None,
) -> Figure:
    """Create an enhanced matplotlib donut chart representing spending by category.

    Transactions with negative amounts are considered expenses and aggregated by category_id.
    Labels are resolved via ``category_lookup`` when provided for readability/accessibility.
    
    Enhanced features:
    - Center total display
    - Legend with amounts and percentages
    - Better color palette
    - Currency formatting
    """

    totals: dict = {}
    grand_total = 0.0

    for tx in transactions:
        cid = getattr(tx, "category_id", "uncategorized") or "uncategorized"
        amt = float(getattr(tx, "amount", 0) or 0)
        if amt >= 0:
            continue
        abs_amt = abs(amt)
        totals[cid] = totals.get(cid, 0) + abs_amt
        grand_total += abs_amt

    # Sort by amount descending for better visualization
    sorted_items = sorted(totals.items(), key=lambda x: x[1], reverse=True)

    labels = [
        category_lookup.get(k, str(k)) if category_lookup else str(k)
        for k, _ in sorted_items
    ]
    sizes = [v for _, v in sorted_items]

    # Calculate percentages
    percentages = [(s / grand_total * 100) if grand_total > 0 else 0 for s in sizes]

    fig, ax = plt.subplots(figsize=(10, 7))

    if sizes:
        # Use a nice color palette
        cmap = plt.get_cmap("tab20c")
        colors = [cmap(i / max(len(sizes), 1)) for i in range(len(sizes))]

        # Create donut chart
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=None,  # We'll use legend instead
            autopct=lambda pct: f'{pct:.1f}%' if pct > 4 else '',
            wedgeprops=dict(width=0.45, edgecolor='white', linewidth=1.5),
            startangle=90,
            colors=colors,
            pctdistance=0.78,
        )

        # Style the percentage labels
        for autotext in autotexts:
            autotext.set_fontsize(9)
            autotext.set_fontweight('bold')
            autotext.set_color('white')

        # Center text with total
        ax.text(0, 0.08, 'Total Spending',
                ha='center', va='center', fontsize=11, color='#666')
        ax.text(0, -0.08, f'${grand_total:,.0f}',
                ha='center', va='center', fontsize=18, fontweight='bold', color='#1F2937')

        # Create legend with amounts and percentages (top categories only if too many)
        max_legend_items = 12
        display_items = min(len(labels), max_legend_items)

        legend_labels = [
            f'{labels[i]}: ${sizes[i]:,.0f} ({percentages[i]:.1f}%)'
            for i in range(display_items)
        ]

        if len(labels) > max_legend_items:
            # Add "Other" category to legend
            other_total = sum(sizes[max_legend_items:])
            other_pct = sum(percentages[max_legend_items:])
            legend_labels.append(f'Other ({len(labels) - max_legend_items} more): ${other_total:,.0f} ({other_pct:.1f}%)')

        ax.legend(
            wedges[:display_items] + ([wedges[-1]] if len(labels) > max_legend_items else []),
            legend_labels,
            title="Categories",
            title_fontsize=11,
            loc="center left",
            bbox_to_anchor=(1.02, 0.5),
            fontsize=9,
            framealpha=0.9,
        )

        ax.axis("equal")
        ax.set_title("Spending by Category", fontsize=16, fontweight='bold', pad=20)

        # Add summary stats box
        num_categories = len(labels)
        avg_per_category = grand_total / num_categories if num_categories > 0 else 0
        top_category = labels[0] if labels else "N/A"
        top_amount = sizes[0] if sizes else 0

        stats_text = f'Categories: {num_categories}\nTop: {top_category}\n(${top_amount:,.0f})'
        props = dict(boxstyle='round,pad=0.5', facecolor='#F3F4F6', alpha=0.9, edgecolor='#E5E7EB')
        ax.text(0.02, 0.98, stats_text, transform=ax.transAxes, fontsize=9,
                verticalalignment='top', bbox=props, color='#374151')

    else:
        ax.text(0.5, 0.5, "No expense data", ha="center", va="center", fontsize=14, color="#666")
        ax.axis("off")

    plt.tight_layout()
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
        fig.savefig(output_path, bbox_inches="tight", dpi=120)
    plt.close(fig)
    return output_path

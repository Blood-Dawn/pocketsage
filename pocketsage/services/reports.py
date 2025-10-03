"""Reporting utilities for PocketSage."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Protocol

from matplotlib.figure import Figure

from ..models.transaction import Transaction


class ReportRenderer(Protocol):
    """Protocol describing renderer behavior."""

    def render(self, figure: Figure, *, output_path: Path) -> None:  # pragma: no cover - interface
        ...


def build_spending_chart(*, transactions: Iterable[Transaction]) -> Figure:
    """Create a matplotlib figure representing spending by category."""

    # TODO(@visuals): implement aggregation + color palette + legend layout.
    raise NotImplementedError


def export_transactions_csv(*, transactions: Iterable[Transaction], output_path: Path) -> None:
    """Write transaction data to CSV at the desired location."""

    # TODO(@teammate): implement CSV writing with deterministic column ordering + quoting.
    raise NotImplementedError


def export_spending_png(
    *, transactions: Iterable[Transaction], output_path: Path, renderer: ReportRenderer
) -> Path:
    """Render spending chart to PNG using provided renderer, return resulting path."""

    # TODO(@teammate): build figure via build_spending_chart and call renderer.render.
    raise NotImplementedError

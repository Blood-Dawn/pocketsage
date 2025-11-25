"""Heavy randomized seed helper for admin testing."""

from __future__ import annotations

import time
from contextlib import AbstractContextManager
from typing import Callable, Optional

from sqlmodel import Session

from .admin_tasks import (
    SeedMetrics,
    SeedProfile,
    SeedSummary,
    _run_heavy_seed_internal,
)

SessionFactory = Callable[[], AbstractContextManager[Session]]


def run_heavy_seed(
    session_factory: Optional[SessionFactory] = None, *, user_id: int
) -> SeedSummary:
    """Reset transactions and seed a randomized heavy dataset.

    Returns:
        SeedSummary with counts of seeded data.
    """
    return _run_heavy_seed_internal(session_factory, user_id=user_id)


def run_heavy_seed_with_metrics(
    session_factory: Optional[SessionFactory] = None, *, user_id: int
) -> SeedMetrics:
    """Reset transactions and seed a randomized heavy dataset with performance metrics.

    Returns:
        SeedMetrics containing the seed summary and timing information.
    """
    start_time = time.perf_counter()
    summary = _run_heavy_seed_internal(session_factory, user_id=user_id)
    elapsed = time.perf_counter() - start_time
    return SeedMetrics(profile=SeedProfile.HEAVY, summary=summary, duration_seconds=elapsed)


__all__ = ["run_heavy_seed", "run_heavy_seed_with_metrics"]

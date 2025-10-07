"""Lightweight background job orchestration utilities."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock, Thread
from typing import Any, Callable, Dict, Iterable, Optional
from uuid import uuid4

__all__ = [
    "Job",
    "enqueue",
    "get_job",
    "list_jobs",
    "set_async_execution",
    "clear_jobs",
]


@dataclass
class Job:
    """Simple in-memory representation of a background job."""

    id: str
    name: str
    status: str
    created_at: datetime
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "error": self.error,
            "metadata": self.metadata,
        }


_JOBS: Dict[str, Job] = {}
_LOCK = Lock()
_MAX_JOBS = 100
_RUN_ASYNC = True


def set_async_execution(enabled: bool) -> None:
    """Configure whether jobs run in threads (True) or synchronously (False)."""

    global _RUN_ASYNC
    _RUN_ASYNC = enabled


def clear_jobs() -> None:
    """Remove all tracked jobs (useful for tests)."""

    with _LOCK:
        _JOBS.clear()


def _store_job(job: Job) -> None:
    with _LOCK:
        _JOBS[job.id] = job
        if len(_JOBS) > _MAX_JOBS:
            # Prune oldest jobs to keep memory bounded.
            for job_id in sorted(_JOBS, key=lambda key: _JOBS[key].created_at)[
                : len(_JOBS) - _MAX_JOBS
            ]:
                _JOBS.pop(job_id, None)


def _snapshot_jobs() -> Iterable[Job]:
    with _LOCK:
        return list(_JOBS.values())


def enqueue(
    name: str,
    target: Callable[..., Any],
    *,
    metadata: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Job:
    """Schedule ``target`` for execution and return the tracked job."""

    job = Job(
        id=uuid4().hex,
        name=name,
        status="queued",
        created_at=datetime.now(timezone.utc),
        metadata=metadata or {},
    )
    _store_job(job)

    def runner() -> None:
        job.status = "running"
        job.started_at = datetime.now(timezone.utc)
        try:
            target(**kwargs)
        except Exception as exc:  # pragma: no cover - surfaced via job status checks
            job.status = "failed"
            job.error = str(exc)
        else:
            job.status = "succeeded"
        finally:
            job.finished_at = datetime.now(timezone.utc)

    if _RUN_ASYNC:
        thread = Thread(target=runner, name=f"PocketSageJob-{job.id}", daemon=True)
        thread.start()
    else:
        runner()

    return job


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Return job metadata for ``job_id`` (or ``None`` if unknown)."""

    with _LOCK:
        job = _JOBS.get(job_id)
    return job.to_dict() if job else None


def list_jobs(limit: Optional[int] = None) -> Iterable[Dict[str, Any]]:
    """Return tracked jobs ordered by most recent creation time."""

    jobs = sorted(_snapshot_jobs(), key=lambda job: job.created_at, reverse=True)
    if limit is not None:
        jobs = jobs[:limit]
    return [job.to_dict() for job in jobs]

"""Background task scheduler for periodic operations."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:
    from .context import AppContext

logger = logging.getLogger("pocketsage.scheduler")


class BackgroundScheduler:
    """Manages background tasks for auto-backup and maintenance."""

    def __init__(self, ctx: AppContext):
        """Initialize the scheduler with app context.

        Args:
            ctx: Application context with repositories and config
        """
        self.ctx = ctx
        self.scheduler = None

    def start(self) -> None:
        """Start the background scheduler."""
        try:
            from apscheduler.schedulers.background import BackgroundScheduler as APScheduler
            from apscheduler.triggers.cron import CronTrigger
        except ImportError:
            logger.warning(
                "APScheduler not installed. Background tasks disabled. "
                "Install with: pip install apscheduler"
            )
            return

        if self.scheduler is not None:
            logger.warning("Scheduler already running")
            return

        self.scheduler = APScheduler()

        # Schedule nightly backup at 3 AM
        if self._is_backup_enabled():
            self.scheduler.add_job(
                func=self._run_backup,
                trigger=CronTrigger(hour=3, minute=0),
                id="nightly_backup",
                name="Nightly Database Backup",
                replace_existing=True,
            )
            logger.info("Scheduled nightly backup at 3:00 AM")

        # Schedule log rotation check daily at 4 AM
        self.scheduler.add_job(
            func=self._rotate_logs,
            trigger=CronTrigger(hour=4, minute=0),
            id="log_rotation",
            name="Log Rotation Check",
            replace_existing=True,
        )
        logger.info("Scheduled log rotation check at 4:00 AM")

        # Start the scheduler
        self.scheduler.start()
        logger.info("Background scheduler started")

    def stop(self) -> None:
        """Stop the background scheduler gracefully."""
        if self.scheduler is not None:
            self.scheduler.shutdown(wait=True)
            self.scheduler = None
            logger.info("Background scheduler stopped")

    def _is_backup_enabled(self) -> bool:
        """Check if automatic backups are enabled."""
        # Check settings repository for user preference
        if setting := self.ctx.settings_repo.get("auto_backup_enabled"):
            return setting.value.lower() in ("true", "1", "yes")
        return False  # Default: disabled

    def _run_backup(self) -> None:
        """Execute the backup task."""
        try:
            from .services.admin_tasks import create_backup

            logger.info("Starting scheduled backup")
            uid = self.ctx.require_user_id()

            backup_path = create_backup(
                session_factory=self.ctx.session_factory,
                user_id=uid,
                export_dir=Path(self.ctx.config.DATA_DIR) / "backups" / "auto",
            )

            logger.info(f"Scheduled backup completed: {backup_path}")

        except Exception as exc:
            logger.error(f"Scheduled backup failed: {exc}", exc_info=True)

    def _rotate_logs(self) -> None:
        """Check and rotate logs if needed."""
        try:
            logs_dir = Path(self.ctx.config.DATA_DIR) / "logs"
            if not logs_dir.exists():
                return

            # Clean up old log files (keep last 30 days)
            max_age_days = 30
            cutoff = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)

            for log_file in logs_dir.glob("*.log.*"):
                if log_file.stat().st_mtime < cutoff:
                    log_file.unlink()
                    logger.info(f"Deleted old log file: {log_file.name}")

        except Exception as exc:
            logger.error(f"Log rotation failed: {exc}", exc_info=True)

    def add_job(
        self,
        func: Callable,
        trigger: str,
        *,
        job_id: str,
        name: str | None = None,
        **trigger_args,
    ) -> None:
        """Add a custom job to the scheduler.

        Args:
            func: Function to execute
            trigger: Trigger type ('cron', 'interval', 'date')
            job_id: Unique job identifier
            name: Human-readable job name
            **trigger_args: Additional trigger arguments
        """
        if self.scheduler is None:
            logger.warning(f"Cannot add job {job_id}: scheduler not started")
            return

        try:
            if trigger == "cron":
                from apscheduler.triggers.cron import CronTrigger

                trigger_obj = CronTrigger(**trigger_args)
            elif trigger == "interval":
                from apscheduler.triggers.interval import IntervalTrigger

                trigger_obj = IntervalTrigger(**trigger_args)
            elif trigger == "date":
                from apscheduler.triggers.date import DateTrigger

                trigger_obj = DateTrigger(**trigger_args)
            else:
                raise ValueError(f"Unknown trigger type: {trigger}")

            self.scheduler.add_job(
                func=func,
                trigger=trigger_obj,
                id=job_id,
                name=name or job_id,
                replace_existing=True,
            )
            logger.info(f"Added job: {job_id}")

        except Exception as exc:
            logger.error(f"Failed to add job {job_id}: {exc}", exc_info=True)

    def remove_job(self, job_id: str) -> None:
        """Remove a job from the scheduler.

        Args:
            job_id: Job identifier to remove
        """
        if self.scheduler is not None:
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed job: {job_id}")


def create_scheduler(ctx: AppContext, *, auto_start: bool = False) -> BackgroundScheduler:
    """Create and optionally start a background scheduler.

    Args:
        ctx: Application context
        auto_start: Whether to start the scheduler immediately

    Returns:
        BackgroundScheduler instance
    """
    scheduler = BackgroundScheduler(ctx)
    if auto_start:
        scheduler.start()
    return scheduler

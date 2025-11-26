"""Structured logging configuration with JSON output and rotation."""

from __future__ import annotations

import atexit
import json
import logging
import logging.handlers
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from .config import BaseConfig

_SESSION_BUFFER: List[str] = []
_SESSION_START = datetime.now()
_SESSION_LOG_PATH: Path | None = None


class SessionBufferHandler(logging.Handler):
    """In-memory handler to collect all log lines for the current app session.

    Flushed to a timestamped file when the application exits (atexit).
    """

    def __init__(self, formatter: logging.Formatter):
        super().__init__()
        self._formatter = formatter

    def emit(self, record: logging.LogRecord) -> None:  # noqa: D401
        try:
            line = self._formatter.format(record)
            _SESSION_BUFFER.append(line)
        except Exception:  # pragma: no cover - defensive
            pass


class JSONFormatter(logging.Formatter):
    """Format log records as JSON for structured logging."""

    # Standard LogRecord attributes that should not be treated as extra fields
    _STANDARD_ATTRS = {
        "name", "msg", "args", "created", "filename", "funcName", "levelname",
        "levelno", "lineno", "module", "msecs", "message", "pathname", "process",
        "processName", "relativeCreated", "thread", "threadName", "exc_info",
        "exc_text", "stack_info", "getMessage", "stack_trace",
    }

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record as a JSON string."""
        log_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info) if record.exc_info else None,
            }

        # Add extra fields from record.__dict__ (those passed via logger.info(..., extra={...}))
        extra_fields = {
            key: value
            for key, value in record.__dict__.items()
            if key not in self._STANDARD_ATTRS
        }
        if extra_fields:
            log_data["extra"] = extra_fields

        return json.dumps(log_data, default=str)


def setup_logging(config: BaseConfig) -> logging.Logger:
    """Configure structured logging with JSON format and file rotation.

    Args:
        config: Application configuration with DATA_DIR

    Returns:
        Configured root logger
    """
    # Create logs directory
    logs_dir = Path(config.DATA_DIR) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    # Configure root logger
    root_logger = logging.getLogger("pocketsage")
    root_logger.setLevel(logging.INFO)

    # Remove existing handlers to avoid duplicates
    root_logger.handlers.clear()

    # Console handler (human-readable format for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO if config.DEV_MODE else logging.WARNING)

    # Choose format based on dev mode
    if config.DEV_MODE:
        console_format = "[%(asctime)s] %(levelname)-8s [%(name)s.%(funcName)s:%(lineno)d] %(message)s"
    else:
        console_format = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

    console_formatter = logging.Formatter(
        fmt=console_format,
        datefmt="%H:%M:%S" if config.DEV_MODE else "%Y-%m-%d %H:%M:%S",
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # File handler with rotation (JSON format for production)
    log_file = logs_dir / "pocketsage.log"
    file_handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=10 * 1024 * 1024,  # 10 MB
        backupCount=5,  # Keep 5 old log files
        encoding="utf-8",
    )
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(JSONFormatter())
    root_logger.addHandler(file_handler)

    # Session buffer handler (captures EXACT console formatted lines for post-mortem)
    session_handler = SessionBufferHandler(console_formatter)
    session_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(session_handler)

    # Prepare session log path & atexit flush
    global _SESSION_LOG_PATH  # noqa: PLW0603
    session_filename = _SESSION_START.strftime("session_%Y%m%d_%H%M%S.log")
    _SESSION_LOG_PATH = (Path(config.DATA_DIR) / "logs" / session_filename)

    def _flush_session():  # pragma: no cover - side-effect
        if not _SESSION_BUFFER:
            return
        try:
            _SESSION_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with _SESSION_LOG_PATH.open("w", encoding="utf-8") as f:
                f.write("# PocketSage session log\n")
                f.write(f"# Started: {_SESSION_START.isoformat()} UTC\n")
                f.write(f"# Entries: {len(_SESSION_BUFFER)}\n\n")
                for line in _SESSION_BUFFER:
                    f.write(line + "\n")
        except Exception as e:  # pragma: no cover
            # Last resort direct stderr write; avoid raising during interpreter shutdown
            import sys
            sys.stderr.write(f"Failed to flush session log: {e}\n")

    atexit.register(_flush_session)

    # Log startup message
    root_logger.info(
        "Logging initialized",
        extra={
            "dev_mode": config.DEV_MODE,
            "log_file": str(log_file),
            "data_dir": config.DATA_DIR,
        },
    )

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for a specific module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(f"pocketsage.{name}")


def session_log_path() -> Path | None:
    """Return the path where the in-memory session log will be flushed on exit."""
    return _SESSION_LOG_PATH

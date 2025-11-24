"""Tests for structured logging functionality."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from pocketsage.config import BaseConfig
from pocketsage.logging_config import JSONFormatter, get_logger, setup_logging


def test_json_formatter():
    """Test that JSONFormatter correctly formats log records."""
    formatter = JSONFormatter()

    # Create a log record
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname="test.py",
        lineno=42,
        msg="Test message",
        args=(),
        exc_info=None,
    )
    record.module = "test_module"
    record.funcName = "test_function"

    # Format the record
    formatted = formatter.format(record)

    # Parse JSON
    log_data = json.loads(formatted)

    # Verify structure
    assert log_data["level"] == "INFO"
    assert log_data["logger"] == "test.logger"
    assert log_data["message"] == "Test message"
    assert log_data["module"] == "test_module"
    assert log_data["function"] == "test_function"
    assert log_data["line"] == 42
    assert "timestamp" in log_data


def test_json_formatter_with_exception():
    """Test that JSONFormatter correctly handles exceptions."""
    formatter = JSONFormatter()

    try:
        raise ValueError("Test error")
    except ValueError:
        import sys

        exc_info = sys.exc_info()

    record = logging.LogRecord(
        name="test.logger",
        level=logging.ERROR,
        pathname="test.py",
        lineno=42,
        msg="Error occurred",
        args=(),
        exc_info=exc_info,
    )
    record.module = "test_module"
    record.funcName = "test_function"

    formatted = formatter.format(record)
    log_data = json.loads(formatted)

    assert "exception" in log_data
    assert log_data["exception"]["type"] == "ValueError"
    assert "Test error" in log_data["exception"]["message"]
    assert log_data["exception"]["traceback"] is not None


def test_setup_logging(tmp_path):
    """Test that logging setup creates log files with rotation."""
    config = BaseConfig()
    config.DATA_DIR = str(tmp_path)
    config.DEV_MODE = True

    # Setup logging
    logger = setup_logging(config)

    # Verify logger is configured
    assert logger.name == "pocketsage"
    assert logger.level == logging.INFO

    # Verify handlers
    assert len(logger.handlers) == 2  # Console + File

    # Verify log directory and file created
    logs_dir = tmp_path / "logs"
    assert logs_dir.exists()

    log_file = logs_dir / "pocketsage.log"
    assert log_file.exists()

    # Log some messages
    logger.info("Test info message")
    logger.warning("Test warning message")
    logger.error("Test error message")

    # Read log file and verify JSON format
    content = log_file.read_text()
    lines = content.strip().split("\n")

    assert len(lines) >= 1  # At least the startup message

    # Verify each line is valid JSON
    for line in lines:
        if line.strip():
            log_entry = json.loads(line)
            assert "timestamp" in log_entry
            assert "level" in log_entry
            assert "message" in log_entry


def test_get_logger():
    """Test that get_logger returns properly namespaced loggers."""
    logger1 = get_logger("module1")
    logger2 = get_logger("module2")

    assert logger1.name == "pocketsage.module1"
    assert logger2.name == "pocketsage.module2"
    assert logger1 != logger2


@pytest.mark.parametrize("dev_mode", [True, False])
def test_logging_levels_by_mode(tmp_path, dev_mode):
    """Test that console logging level adjusts based on dev mode."""
    config = BaseConfig()
    config.DATA_DIR = str(tmp_path)
    config.DEV_MODE = dev_mode

    logger = setup_logging(config)

    # Find console handler
    console_handler = None
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(
            handler, logging.handlers.RotatingFileHandler
        ):
            console_handler = handler
            break

    assert console_handler is not None

    expected_level = logging.INFO if dev_mode else logging.WARNING
    assert console_handler.level == expected_level

"""invst — Centralized logging configuration.

Provides utilities to configure application-wide logging with both console (StreamHandler)
and rotating file (RotatingFileHandler) handlers, reading defaults from the application
configuration (settings.yaml) and environment variables when available.
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from invst.config import get_config, get_project_root

# Default log format as specified in project requirements
DEFAULT_LOG_FORMAT = "%(asctime)s | %(name)s | %(levelname)s | %(message)s"
DEFAULT_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
DEFAULT_MAX_BYTES = 10 * 1024 * 1024  # 10 MB
DEFAULT_BACKUP_COUNT = 5


def _resolve_log_level(level: str | int | None) -> int:
    """Resolve a log level string or int to a standard logging int level.

    Args:
        level: Optional log level name (e.g. 'DEBUG', 'INFO') or int (e.g. logging.INFO).

    Returns:
        int: Standard logging level constant.
    """
    if level is not None:
        if isinstance(level, int):
            return level
        return getattr(logging, str(level).strip().upper(), logging.INFO)

    # Check environment variable override
    env_level = os.environ.get("INVST_LOG_LEVEL")
    if env_level:
        return getattr(logging, env_level.strip().upper(), logging.INFO)

    # Read from config if available
    try:
        cfg = get_config()
        cfg_level = cfg.get("logging", {}).get("level", "INFO")
        if isinstance(cfg_level, int):
            return cfg_level
        return getattr(logging, str(cfg_level).strip().upper(), logging.INFO)
    except Exception:
        return logging.INFO


def _resolve_log_file(log_file: str | Path | None) -> Path | None:
    """Resolve the destination log file path.

    Args:
        log_file: Optional file path for the log file.

    Returns:
        Optional[Path]: Resolved absolute Path to the log file, or None if disabled.
    """
    if log_file is not None:
        return Path(log_file).resolve()

    # Check environment variable override
    env_file = os.environ.get("INVST_LOG_FILE")
    if env_file:
        return Path(env_file).resolve()

    # Read from config if available
    try:
        cfg = get_config()
        cfg_file = cfg.get("logging", {}).get("file")
        if cfg_file:
            return Path(cfg_file).resolve()
    except Exception:
        pass

    # Fallback default: <project_root>/logs/invst.log
    try:
        return (get_project_root() / "logs" / "invst.log").resolve()
    except Exception:
        return Path("logs/invst.log").resolve()


def _resolve_log_format(log_format: str | None) -> str:
    """Resolve log record formatting string.

    Args:
        log_format: Optional formatting template string.

    Returns:
        str: Format string to use with logging.Formatter.
    """
    if log_format:
        return log_format

    try:
        cfg = get_config()
        cfg_format = cfg.get("logging", {}).get("format")
        if cfg_format:
            return str(cfg_format)
    except Exception:
        pass

    return DEFAULT_LOG_FORMAT


def setup_logging(
    level: str | int | None = None,
    log_file: str | Path | None = None,
    log_format: str | None = None,
    date_format: str = DEFAULT_DATE_FORMAT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    backup_count: int = DEFAULT_BACKUP_COUNT,
) -> logging.Logger:
    """Configure and return the root application logger for 'invst'.

    Sets up:
      1. A console StreamHandler writing to sys.stdout.
      2. A RotatingFileHandler writing to the specified or configured log file.
         The log directory will be created automatically if it does not exist.

    If level or log_file are not provided as arguments, defaults are loaded
    from the application configuration (settings.yaml) and environment variables.

    Args:
        level: Logging level (e.g. 'DEBUG', 'INFO', or logging.INFO). Defaults to config.
        log_file: File path for the rotating log file. Defaults to config or logs/invst.log.
        log_format: Format string for log messages. Defaults to
            '%(asctime)s | %(name)s | %(levelname)s | %(message)s'.
        date_format: Date format for log timestamps. Defaults to '%Y-%m-%d %H:%M:%S'.
        max_bytes: Maximum size of a log file before rotation in bytes (default 10 MB).
        backup_count: Number of rotated backup files to retain (default 5).

    Returns:
        logging.Logger: The configured 'invst' logger instance.
    """
    resolved_level = _resolve_log_level(level)
    resolved_file = _resolve_log_file(log_file)
    fmt_str = _resolve_log_format(log_format)
    formatter = logging.Formatter(fmt=fmt_str, datefmt=date_format)

    logger = logging.getLogger("invst")
    logger.setLevel(resolved_level)

    # Remove existing handlers to ensure idempotency and prevent duplicate messages
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    # Console output handler (sys.stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(resolved_level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Rotating file output handler
    if resolved_file is not None:
        try:
            resolved_file.parent.mkdir(parents=True, exist_ok=True)
            file_handler = RotatingFileHandler(
                filename=str(resolved_file),
                maxBytes=max_bytes,
                backupCount=backup_count,
                encoding="utf-8",
            )
            file_handler.setLevel(resolved_level)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except OSError as err:
            logger.warning("Could not initialize log file at %s: %s", resolved_file, err)

    # Avoid propagation to the root logger to prevent duplicate console messages
    logger.propagate = False

    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Retrieve an invst logger or sub-logger by name.

    If name is None or 'invst', returns the main 'invst' logger.
    If a module name is provided (e.g. 'ingestion.bhavcopy'), returns 'invst.ingestion.bhavcopy'.

    Args:
        name: Sub-logger name or None for the root invst logger.

    Returns:
        logging.Logger: The requested logger instance.
    """
    if not name or name == "invst":
        return logging.getLogger("invst")
    if name.startswith("invst."):
        return logging.getLogger(name)
    return logging.getLogger(f"invst.{name}")

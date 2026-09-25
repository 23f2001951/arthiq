"""Tests for invst.logging_utils module."""

import logging
from pathlib import Path

from invst.config import Config
from invst.logging_utils import get_logger, setup_logging


def test_setup_logging_creates_logger(tmp_path: Path) -> None:
    """Test setup_logging configures console and rotating file handlers."""
    log_file = tmp_path / "test_logs" / "test.log"
    logger = setup_logging(level="DEBUG", log_file=log_file)

    assert logger.name == "invst"
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) >= 2  # StreamHandler + RotatingFileHandler

    logger.debug("Debug test entry")
    logger.info("Info test entry")

    assert log_file.is_file()
    content = log_file.read_text(encoding="utf-8")
    assert "Debug test entry" in content
    assert "Info test entry" in content
    assert "| invst | DEBUG |" in content


def test_get_logger_subloggers() -> None:
    """Test get_logger returns correctly prefixed subloggers."""
    root_logger = get_logger()
    assert root_logger.name == "invst"

    sub = get_logger("scoring.quality")
    assert sub.name == "invst.scoring.quality"

    already_prefixed = get_logger("invst.scoring.quality")
    assert already_prefixed.name == "invst.scoring.quality"


def test_setup_logging_defaults(sample_config: Config) -> None:
    """Test setup_logging uses defaults from config when arguments are None."""
    logger = setup_logging()
    assert logger.name == "invst"
    # Should resolve to INFO from settings.yaml
    assert logger.level == logging.INFO

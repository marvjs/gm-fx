"""Logging tests."""

import logging
from pathlib import Path

from grandmaster_fx.infrastructure.logging import configure_logging


def test_configure_logging_is_idempotent(tmp_path: Path) -> None:
    logger = configure_logging("INFO", tmp_path)
    same_logger = configure_logging("DEBUG", tmp_path)

    assert same_logger is logger
    assert logger.level == logging.DEBUG
    assert len(logger.handlers) == 2
    assert (tmp_path / "grandmaster-fx.log").is_file()

"""Idempotent console and rotating-file logging setup."""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from rich.logging import RichHandler

LOGGER_NAME = "grandmaster_fx"


def configure_logging(level: str, log_directory: Path) -> logging.Logger:
    """Configure application logging and return the package logger."""
    log_directory.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    for handler in logger.handlers[:]:
        handler.close()
        logger.removeHandler(handler)

    console_handler = RichHandler(
        markup=False,
        rich_tracebacks=True,
        show_path=False,
        show_time=True,
    )
    console_handler.setLevel(level)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    file_handler = RotatingFileHandler(
        log_directory / "grandmaster-fx.log",
        maxBytes=5_000_000,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )
    )

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

"""Shared tests and fixtures."""

from pathlib import Path

import pytest


@pytest.fixture
def valid_config_text(tmp_path: Path) -> str:
    """Return valid TOML with output paths isolated to a test directory."""
    log_directory = (tmp_path / "logs").as_posix()
    data_directory = (tmp_path / "data").as_posix()
    return f"""
[app]
name = "Grandmaster FX Test"
environment = "test"
log_level = "DEBUG"
log_directory = "{log_directory}"
data_directory = "{data_directory}"

[execution]
mode = "observe"
allow_live_account = false
"""

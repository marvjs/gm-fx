"""TOML configuration loading."""

import tomllib
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from grandmaster_fx.config.models import AppSettings
from grandmaster_fx.exceptions import ConfigurationError, SafetyViolationError

DEFAULT_CONFIG_PATH = Path("configs/app.toml")


def _read_toml(path: Path) -> dict[str, Any]:
    try:
        with path.open("rb") as config_file:
            return tomllib.load(config_file)
    except FileNotFoundError as error:
        message = f"Configuration file not found: {path}"
        raise ConfigurationError(message) from error
    except tomllib.TOMLDecodeError as error:
        message = f"Configuration file is not valid TOML: {path}: {error}"
        raise ConfigurationError(message) from error
    except OSError as error:
        message = f"Configuration file could not be read: {path}: {error}"
        raise ConfigurationError(message) from error


def load_settings(path: Path = DEFAULT_CONFIG_PATH) -> AppSettings:
    """Load and validate application settings from TOML."""
    raw = _read_toml(path)
    try:
        return AppSettings.model_validate(raw)
    except SafetyViolationError:
        raise
    except ValidationError as error:
        message = f"Configuration validation failed for {path}: {error}"
        raise ConfigurationError(message) from error

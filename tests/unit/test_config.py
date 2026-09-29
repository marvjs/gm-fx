"""Configuration loading tests."""

from pathlib import Path

import pytest

from grandmaster_fx.config import Environment, ExecutionMode, load_settings
from grandmaster_fx.exceptions import ConfigurationError, SafetyViolationError


def test_load_settings_accepts_valid_toml(tmp_path: Path, valid_config_text: str) -> None:
    config_path = tmp_path / "app.toml"
    config_path.write_text(valid_config_text, encoding="utf-8")

    settings = load_settings(config_path)

    assert settings.app.environment is Environment.TEST
    assert settings.execution.mode is ExecutionMode.OBSERVE
    assert settings.execution.allow_live_account is False


def test_load_settings_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="not found"):
        load_settings(tmp_path / "missing.toml")


def test_load_settings_rejects_invalid_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "broken.toml"
    config_path.write_text("[app\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="not valid TOML"):
        load_settings(config_path)


def test_load_settings_rejects_unknown_keys(tmp_path: Path, valid_config_text: str) -> None:
    config_path = tmp_path / "app.toml"
    config_path.write_text(f"{valid_config_text}\nunknown = true\n", encoding="utf-8")

    with pytest.raises(ConfigurationError, match="validation failed"):
        load_settings(config_path)


def test_live_account_flag_is_always_rejected(tmp_path: Path, valid_config_text: str) -> None:
    config_path = tmp_path / "app.toml"
    unsafe = valid_config_text.replace("allow_live_account = false", "allow_live_account = true")
    config_path.write_text(unsafe, encoding="utf-8")

    with pytest.raises(SafetyViolationError, match="Live-account execution is prohibited"):
        load_settings(config_path)

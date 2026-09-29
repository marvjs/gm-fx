"""Experiment configuration tests."""

from pathlib import Path

import pytest

from grandmaster_fx.config.experiments import load_experiment_settings
from grandmaster_fx.exceptions import ConfigurationError


def test_default_experiment_manifest_loads() -> None:
    settings = load_experiment_settings()
    identifiers = {item.id for item in settings.strategies}
    assert {
        "session_range_breakout",
        "fibonacci_pullback",
        "channel_mean_reversion",
        "momentum_continuation",
    } <= identifiers
    assert settings.eligibility.execution_enabled is False


def test_missing_manifest_is_wrapped(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="invalid"):
        load_experiment_settings(tmp_path / "missing.toml")


def test_duplicate_strategy_identifiers_are_rejected(tmp_path: Path) -> None:
    source = Path("configs/experiments.toml").read_text(encoding="utf-8")
    duplicated = source.replace('id = "donchian_breakout"', 'id = "baseline_scalper"')
    path = tmp_path / "experiments.toml"
    path.write_text(duplicated, encoding="utf-8")
    with pytest.raises(ConfigurationError, match="identifiers"):
        load_experiment_settings(path)

"""Baseline strategy configuration tests."""

from pathlib import Path

import pytest

from grandmaster_fx.config.strategy import load_strategy_settings
from grandmaster_fx.exceptions import ConfigurationError

VALID = """
[strategy]
name="test"
enabled=true
fast_ema_period=3
slow_ema_period=5
rsi_period=3
atr_period=3
roc_period=2
minimum_bars=10
[filters]
max_spread_points=15
minimum_atr_points=1.0
maximum_atr_points=100.0
minimum_roc_percent=0.0
buy_rsi_min=50.0
buy_rsi_max=80.0
sell_rsi_min=20.0
sell_rsi_max=50.0
session_start_utc=0
session_end_utc=24
[protection]
stop_atr_multiple=1.0
target_atr_multiple=2.0
minimum_reward_risk=1.5
"""


def test_valid_strategy_configuration(tmp_path: Path) -> None:
    path = tmp_path / "strategy.toml"
    path.write_text(VALID, encoding="utf-8")
    settings = load_strategy_settings(path)
    assert settings.strategy.fast_ema_period == 3
    assert settings.protection.target_atr_multiple == 2.0


def test_invalid_period_order_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "strategy.toml"
    path.write_text(
        VALID.replace("fast_ema_period=3", "fast_ema_period=6"),
        encoding="utf-8",
    )
    with pytest.raises(ConfigurationError, match="invalid"):
        load_strategy_settings(path)

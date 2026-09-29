"""Backtest configuration loading tests."""

from pathlib import Path

import pytest

from grandmaster_fx.config.backtest import load_backtest_settings
from grandmaster_fx.exceptions import ConfigurationError

VALID = """
[backtest]
initial_balance=10000
risk_per_trade_percent=0.25
commission_per_lot_round_turn=7
slippage_points=2
maximum_holding_bars=20
minimum_history_bars=60
conservative_same_bar_exit=true
[quality]
maximum_gap_multiple=3
maximum_data_age_hours=24
"""


def test_load_backtest_settings(tmp_path: Path) -> None:
    path = tmp_path / "backtest.toml"
    path.write_text(VALID, encoding="utf-8")
    assert load_backtest_settings(path).backtest.initial_balance == 10_000


def test_invalid_backtest_settings_are_wrapped(tmp_path: Path) -> None:
    path = tmp_path / "backtest.toml"
    path.write_text(VALID.replace("initial_balance=10000", "initial_balance=0"), encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid"):
        load_backtest_settings(path)


def test_missing_backtest_file_is_wrapped(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="invalid"):
        load_backtest_settings(tmp_path / "missing.toml")

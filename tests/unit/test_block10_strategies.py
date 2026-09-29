"""Block 10 strategy hypothesis tests."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.strategies.extreme_reversion import (
    ExtremeMeanReversionStrategy,
    ReversionFilters,
    ReversionParameters,
    ReversionProtection,
    ReversionSettings,
    load_extreme_mean_reversion,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal
from grandmaster_fx.strategies.volatility_expansion import (
    ExpansionFilters,
    ExpansionParameters,
    ExpansionProtection,
    ExpansionSettings,
    VolatilityExpansionStrategy,
    load_volatility_expansion,
)


def bar(*, opened: float = 1.0, closed: float = 1.1) -> Bar:
    return Bar(
        datetime(2026, 1, 1, 12, tzinfo=UTC),
        opened,
        max(opened, closed) + 0.1,
        min(opened, closed) - 0.1,
        closed,
        10,
        5,
        0,
    )


def expansion_settings() -> ExpansionSettings:
    return ExpansionSettings(
        strategy=ExpansionParameters(
            name="test",
            range_period=3,
            atr_period=3,
            compression_period=4,
            trend_period=4,
            minimum_bars=8,
        ),
        filters=ExpansionFilters(
            max_spread_points=15,
            compression_ratio_max=0.8,
            expansion_ratio_min=1.2,
            minimum_atr_points=1,
            maximum_atr_points=10000,
            session_start_utc=0,
            session_end_utc=24,
        ),
        protection=ExpansionProtection(
            stop_atr_multiple=1,
            target_atr_multiple=2,
            minimum_reward_risk=1,
        ),
    )


def reversion_settings() -> ReversionSettings:
    return ReversionSettings(
        strategy=ReversionParameters(
            name="test",
            mean_period=3,
            atr_period=3,
            rsi_period=3,
            minimum_bars=5,
        ),
        filters=ReversionFilters(
            max_spread_points=15,
            minimum_displacement_atr=2,
            buy_rsi_max=30,
            sell_rsi_min=70,
            minimum_atr_points=1,
            maximum_atr_points=10000,
            session_start_utc=0,
            session_end_utc=24,
        ),
        protection=ReversionProtection(
            stop_atr_multiple=1,
            target_atr_multiple=2,
            minimum_reward_risk=1,
        ),
    )


def test_strategy_identifiers_and_input_validation() -> None:
    expansion = VolatilityExpansionStrategy(expansion_settings())
    reversion = ExtremeMeanReversionStrategy(reversion_settings())
    assert expansion.identifier == "volatility_expansion"
    assert reversion.identifier == "extreme_mean_reversion"
    with pytest.raises(ValueError, match="bars"):
        expansion.evaluate("EURUSDm", [], 0.00001)
    with pytest.raises(ValueError, match="point"):
        reversion.evaluate("EURUSDm", [bar()] * 5, 0)


def test_reversion_signal_requires_extreme_rsi_and_exhaustion() -> None:
    strategy = ExtremeMeanReversionStrategy(reversion_settings())
    assert strategy._reversion_signal(bar(opened=0.9, closed=1.0), -2.5, 20) is Signal.BUY
    assert strategy._reversion_signal(bar(opened=1.1, closed=1.0), 2.5, 80) is Signal.SELL
    assert strategy._reversion_signal(bar(), 0.5, 50) is Signal.HOLD
    assert strategy._hold_reason(0.5, 50) is DecisionReason.EXTREME_NOT_CONFIRMED
    assert strategy._hold_reason(-2.5, 20) is DecisionReason.EXHAUSTION_NOT_CONFIRMED


def test_expansion_breakout_signal_uses_completed_range() -> None:
    import numpy as np

    strategy = VolatilityExpansionStrategy(expansion_settings())
    high = np.asarray([1.0, 1.1, 1.2, 1.3, 1.4], dtype=float)
    low = np.asarray([0.9, 0.8, 0.7, 0.6, 0.5], dtype=float)
    assert strategy._breakout_signal(np.asarray([1.0, 1.0, 1.0, 1.0, 1.5]), high, low) is Signal.BUY
    assert (
        strategy._breakout_signal(np.asarray([1.0, 1.0, 1.0, 1.0, 0.4]), high, low) is Signal.SELL
    )


def test_invalid_strategy_files_are_wrapped(tmp_path: Path) -> None:
    path = tmp_path / "invalid.toml"
    path.write_text("[strategy]\nname='invalid'\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid"):
        load_volatility_expansion(path)
    with pytest.raises(ConfigurationError, match="invalid"):
        load_extreme_mean_reversion(path)

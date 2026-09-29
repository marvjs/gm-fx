"""Expansion-window hypothesis tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.models import Signal
from grandmaster_fx.strategies.volatility_expansion_window import (
    VolatilityExpansionWindowStrategy,
    WindowContext,
    load_volatility_expansion_window,
)


def bars(count: int = 100) -> list[Bar]:
    start = datetime(2026, 1, 1, 6, tzinfo=UTC)
    return [
        Bar(
            start + timedelta(minutes=5 * index),
            1 + index * 0.00001,
            1.001 + index * 0.00001,
            0.999 + index * 0.00001,
            1 + index * 0.00001,
            10,
            5,
            0,
        )
        for index in range(count)
    ]


def strategy() -> VolatilityExpansionWindowStrategy:
    return load_volatility_expansion_window(
        Path("configs/strategies/volatility_expansion_window.toml")
    )


def context(signal_close: float, age: int, current_atr: float) -> WindowContext:
    length = 100
    close = np.full(length, 1.0)
    close[-1] = signal_close
    atr = np.full(length, 0.0005)
    atr[-1] = current_atr
    trend = np.full(length, 1.0)
    upper = np.full(length, 1.01)
    lower = np.full(length, 0.99)
    ages = np.full(length, -1, dtype=np.int64)
    ages[-1] = age
    compression_atr = np.full(length, np.nan)
    compression_atr[-1] = 0.0005
    return WindowContext(close, atr, trend, upper, lower, ages, compression_atr)


def test_fixed_configuration_and_precomputed_context() -> None:
    candidate = strategy()
    prepared = candidate.prepare(bars())
    assert candidate.identifier == "volatility_expansion_window"
    assert candidate.settings.strategy.compression_lookback == 6
    assert candidate.settings.strategy.expansion_window == 3
    assert len(prepared.compression_age) == 100


def test_expansion_inside_window_can_signal() -> None:
    candidate = strategy()
    data = bars()
    latest = data[-1]
    data[-1] = Bar(
        latest.time,
        latest.open,
        1.021,
        latest.low,
        1.02,
        latest.tick_volume,
        latest.spread,
        latest.real_volume,
    )
    decision = candidate.evaluate_at("EURUSDm", data, 99, 0.00001, context(1.02, 2, 0.001))
    assert decision.signal is Signal.BUY


def test_expansion_outside_window_is_rejected() -> None:
    candidate = strategy()
    decision = candidate.evaluate_at("EURUSDm", bars(), 99, 0.00001, context(1.02, 4, 0.01))
    assert decision.signal is Signal.HOLD


def test_wrong_context_is_rejected() -> None:
    with pytest.raises(TypeError, match="WindowContext"):
        strategy().evaluate_at("EURUSDm", bars(), 99, 0.00001, object())

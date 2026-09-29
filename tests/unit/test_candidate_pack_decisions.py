"""Decision-path coverage for the consolidated candidate strategy pack."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import pytest

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.strategies.candidate_pack import (
    CandidateContext,
    load_channel_mean_reversion,
    load_fibonacci_pullback,
    load_momentum_continuation,
    load_session_range_breakout,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal

CONFIG_DIR = Path("configs/strategies")
POINT = 0.00001
LENGTH = 100


def bars(
    *,
    hour: int = 9,
    opened: float = 1.0,
    closed: float = 1.0,
    high: float = 1.0004,
    low: float = 0.9996,
    spread: int = 5,
) -> list[Bar]:
    end = datetime(2026, 1, 1, hour, tzinfo=UTC)
    start = end - timedelta(minutes=5 * (LENGTH - 1))
    return [
        Bar(
            start + timedelta(minutes=5 * index),
            opened,
            high,
            low,
            closed,
            10,
            spread,
            0,
        )
        for index in range(LENGTH)
    ]


def context(
    *,
    atr_value: float = 0.0005,
    primary: float = 1.0,
    secondary: float = 1.0,
    tertiary: float = 1.0,
) -> CandidateContext:
    return CandidateContext(
        close=np.full(LENGTH, 1.0),
        high=np.full(LENGTH, 1.001),
        low=np.full(LENGTH, 0.999),
        atr=np.full(LENGTH, atr_value),
        primary=np.full(LENGTH, primary),
        secondary=np.full(LENGTH, secondary),
        tertiary=np.full(LENGTH, tertiary),
    )


def latest_data(**kwargs: object) -> list[Bar]:
    data = bars()
    latest = data[-1]
    values = {
        "opened": latest.open,
        "closed": latest.close,
        "high": latest.high,
        "low": latest.low,
        "spread": latest.spread,
    }
    values.update(kwargs)
    data[-1] = Bar(
        latest.time,
        float(values["opened"]),
        float(values["high"]),
        float(values["low"]),
        float(values["closed"]),
        latest.tick_volume,
        int(values["spread"]),
        latest.real_volume,
    )
    return data


def test_session_range_breakout_buy_sell_and_hold_paths() -> None:
    strategy = load_session_range_breakout(CONFIG_DIR / "session_range_breakout.toml")
    buy = strategy.evaluate_at(
        "EURUSDm",
        latest_data(closed=1.02, high=1.021),
        99,
        POINT,
        context(primary=1.0, secondary=1.01, tertiary=0.99),
    )
    sell = strategy.evaluate_at(
        "EURUSDm",
        latest_data(closed=0.98, low=0.979),
        99,
        POINT,
        context(primary=1.0, secondary=1.01, tertiary=0.99),
    )
    hold = strategy.evaluate_at(
        "EURUSDm",
        latest_data(),
        99,
        POINT,
        context(primary=1.0, secondary=1.01, tertiary=0.99),
    )
    assert buy.signal is Signal.BUY
    assert sell.signal is Signal.SELL
    assert hold.signal is Signal.HOLD


def test_session_range_quality_rejections() -> None:
    strategy = load_session_range_breakout(CONFIG_DIR / "session_range_breakout.toml")
    outside = strategy.evaluate_at("EURUSDm", bars(hour=14), 99, POINT, context())
    spread = strategy.evaluate_at("EURUSDm", latest_data(spread=99), 99, POINT, context())
    low_volatility = strategy.evaluate_at(
        "EURUSDm", latest_data(), 99, POINT, context(atr_value=0.000001)
    )
    high_volatility = strategy.evaluate_at(
        "EURUSDm", latest_data(), 99, POINT, context(atr_value=0.01)
    )
    assert outside.reasons == (DecisionReason.OUTSIDE_SESSION,)
    assert spread.reasons == (DecisionReason.SPREAD_TOO_WIDE,)
    assert low_volatility.reasons == (DecisionReason.VOLATILITY_TOO_LOW,)
    assert high_volatility.reasons == (DecisionReason.VOLATILITY_TOO_HIGH,)


def test_fibonacci_pullback_buy_sell_and_rejections() -> None:
    strategy = load_fibonacci_pullback(CONFIG_DIR / "fibonacci_pullback.toml")
    buy_context = context(
        atr_value=0.001,
        primary=0.999,
        secondary=1.02,
        tertiary=0.98,
    )
    sell_context = context(
        atr_value=0.001,
        primary=1.01,
        secondary=1.02,
        tertiary=0.98,
    )
    buy = strategy.evaluate_at(
        "EURUSDm",
        latest_data(opened=1.003, closed=1.004, high=1.005),
        99,
        POINT,
        buy_context,
    )
    sell = strategy.evaluate_at(
        "EURUSDm",
        latest_data(opened=0.997, closed=0.996, low=0.995),
        99,
        POINT,
        sell_context,
    )
    weak_impulse = strategy.evaluate_at(
        "EURUSDm",
        latest_data(),
        99,
        POINT,
        context(atr_value=0.001, primary=0.999, secondary=1.0005, tertiary=0.9995),
    )
    bad_retracement = strategy.evaluate_at(
        "EURUSDm",
        latest_data(opened=1.0, closed=1.019),
        99,
        POINT,
        buy_context,
    )
    assert buy.signal is Signal.BUY
    assert sell.signal is Signal.SELL
    assert weak_impulse.reasons == (DecisionReason.EXTREME_NOT_CONFIRMED,)
    assert bad_retracement.reasons == (DecisionReason.EXHAUSTION_NOT_CONFIRMED,)


def test_channel_mean_reversion_buy_sell_and_hold() -> None:
    strategy = load_channel_mean_reversion(CONFIG_DIR / "channel_mean_reversion.toml")
    buy = strategy.evaluate_at(
        "EURUSDm",
        latest_data(opened=0.998, closed=0.999),
        99,
        POINT,
        context(atr_value=0.001, primary=1.0, secondary=20.0),
    )
    sell = strategy.evaluate_at(
        "EURUSDm",
        latest_data(opened=1.002, closed=1.001),
        99,
        POINT,
        context(atr_value=0.001, primary=1.0, secondary=80.0),
    )
    hold = strategy.evaluate_at(
        "EURUSDm",
        latest_data(),
        99,
        POINT,
        context(atr_value=0.001, primary=1.0, secondary=50.0),
    )
    assert buy.signal is Signal.BUY
    assert sell.signal is Signal.SELL
    assert hold.signal is Signal.HOLD


def test_momentum_continuation_buy_sell_and_large_candle_rejection() -> None:
    strategy = load_momentum_continuation(CONFIG_DIR / "momentum_continuation.toml")
    buy = strategy.evaluate_at(
        "EURUSDm",
        latest_data(high=1.0004, low=0.9996),
        99,
        POINT,
        context(atr_value=0.001, primary=1.01, secondary=1.0, tertiary=0.1),
    )
    sell = strategy.evaluate_at(
        "EURUSDm",
        latest_data(high=1.0004, low=0.9996),
        99,
        POINT,
        context(atr_value=0.001, primary=0.99, secondary=1.0, tertiary=-0.1),
    )
    large = strategy.evaluate_at(
        "EURUSDm",
        latest_data(high=1.01, low=0.99),
        99,
        POINT,
        context(atr_value=0.001, primary=1.01, secondary=1.0, tertiary=0.1),
    )
    assert buy.signal is Signal.BUY
    assert sell.signal is Signal.SELL
    assert large.reasons == (DecisionReason.VOLATILITY_TOO_HIGH,)


def test_compatibility_empty_history_and_invalid_configuration(tmp_path: Path) -> None:
    strategy = load_momentum_continuation(CONFIG_DIR / "momentum_continuation.toml")
    with pytest.raises(ValueError, match="bars"):
        strategy.evaluate("EURUSDm", [], POINT)

    invalid = tmp_path / "invalid.toml"
    invalid.write_text("[strategy]\nname='invalid'\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid"):
        load_session_range_breakout(invalid)

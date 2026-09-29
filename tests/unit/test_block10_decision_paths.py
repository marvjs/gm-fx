"""Complete Block 10 public decision-path tests."""

from datetime import UTC, datetime, timedelta

import numpy as np
import pytest

import grandmaster_fx.strategies.extreme_reversion as reversion_module
import grandmaster_fx.strategies.volatility_expansion as expansion_module
from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.extreme_reversion import ExtremeMeanReversionStrategy
from grandmaster_fx.strategies.models import DecisionReason, Signal
from grandmaster_fx.strategies.volatility_expansion import VolatilityExpansionStrategy
from tests.unit.test_block10_strategies import expansion_settings, reversion_settings


def bars(count: int = 10, *, hour: int = 12, spread: int = 5) -> list[Bar]:
    start = datetime(2026, 1, 1, hour, tzinfo=UTC)
    return [
        Bar(
            start + timedelta(minutes=index),
            1 + index * 0.001,
            1.01 + index * 0.001,
            0.99 + index * 0.001,
            1 + index * 0.001,
            10,
            spread,
            0,
        )
        for index in range(count)
    ]


def test_expansion_preflight_paths() -> None:
    strategy = VolatilityExpansionStrategy(expansion_settings())
    assert strategy.evaluate("EURUSDm", bars(3), 0.00001).reasons == (
        DecisionReason.INSUFFICIENT_HISTORY,
    )
    outside = strategy.settings.model_copy(
        update={
            "filters": strategy.settings.filters.model_copy(
                update={"session_start_utc": 13, "session_end_utc": 14}
            )
        }
    )
    assert VolatilityExpansionStrategy(outside).evaluate("EURUSDm", bars(), 0.00001).reasons == (
        DecisionReason.OUTSIDE_SESSION,
    )
    assert strategy.evaluate("EURUSDm", bars(spread=99), 0.00001).reasons == (
        DecisionReason.SPREAD_TOO_WIDE,
    )


def test_expansion_volatility_compression_and_expansion_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy = VolatilityExpansionStrategy(expansion_settings())
    data = bars()
    monkeypatch.setattr(expansion_module, "atr", lambda *_args: np.asarray([0.001] * 10))
    assert strategy.evaluate("EURUSDm", data, 1).reasons == (DecisionReason.VOLATILITY_TOO_LOW,)
    monkeypatch.setattr(expansion_module, "atr", lambda *_args: np.asarray([100.0] * 10))
    assert strategy.evaluate("EURUSDm", data, 0.00001).reasons == (
        DecisionReason.VOLATILITY_TOO_HIGH,
    )
    monkeypatch.setattr(expansion_module, "atr", lambda *_args: np.asarray([0.01] * 10))
    assert strategy.evaluate("EURUSDm", data, 0.00001).reasons == (
        DecisionReason.COMPRESSION_NOT_CONFIRMED,
    )
    values = np.asarray([0.02] * 8 + [0.005, 0.0055])
    monkeypatch.setattr(expansion_module, "atr", lambda *_args: values)
    assert strategy.evaluate("EURUSDm", data, 0.00001).reasons == (
        DecisionReason.EXPANSION_NOT_CONFIRMED,
    )


def test_expansion_actionable_and_no_breakout_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy = VolatilityExpansionStrategy(expansion_settings())
    data = bars()
    values = np.asarray([0.02] * 8 + [0.005, 0.01])
    monkeypatch.setattr(expansion_module, "atr", lambda *_args: values)
    monkeypatch.setattr(
        VolatilityExpansionStrategy,
        "_breakout_signal",
        lambda *_args: Signal.HOLD,
    )
    assert strategy.evaluate("EURUSDm", data, 0.00001).reasons == (
        DecisionReason.BREAKOUT_NOT_CONFIRMED,
    )
    monkeypatch.setattr(
        VolatilityExpansionStrategy,
        "_breakout_signal",
        lambda *_args: Signal.BUY,
    )
    buy = strategy.evaluate("EURUSDm", data, 0.00001)
    assert buy.reasons == (DecisionReason.BUY_EXPANSION_CONFIRMED,)
    monkeypatch.setattr(
        VolatilityExpansionStrategy,
        "_breakout_signal",
        lambda *_args: Signal.SELL,
    )
    sell = strategy.evaluate("EURUSDm", data, 0.00001)
    assert sell.reasons == (DecisionReason.SELL_EXPANSION_CONFIRMED,)


def test_reversion_preflight_and_volatility_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy = ExtremeMeanReversionStrategy(reversion_settings())
    assert strategy.evaluate("EURUSDm", bars(3), 0.00001).reasons == (
        DecisionReason.INSUFFICIENT_HISTORY,
    )
    outside = strategy.settings.model_copy(
        update={
            "filters": strategy.settings.filters.model_copy(
                update={"session_start_utc": 13, "session_end_utc": 14}
            )
        }
    )
    assert ExtremeMeanReversionStrategy(outside).evaluate("EURUSDm", bars(), 0.00001).reasons == (
        DecisionReason.OUTSIDE_SESSION,
    )
    assert strategy.evaluate("EURUSDm", bars(spread=99), 0.00001).reasons == (
        DecisionReason.SPREAD_TOO_WIDE,
    )
    monkeypatch.setattr(reversion_module, "atr", lambda *_args: np.asarray([0.001] * 10))
    assert strategy.evaluate("EURUSDm", bars(), 1).reasons == (DecisionReason.VOLATILITY_TOO_LOW,)
    monkeypatch.setattr(reversion_module, "atr", lambda *_args: np.asarray([100.0] * 10))
    assert strategy.evaluate("EURUSDm", bars(), 0.00001).reasons == (
        DecisionReason.VOLATILITY_TOO_HIGH,
    )


def test_reversion_actionable_and_hold_paths(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy = ExtremeMeanReversionStrategy(reversion_settings())
    data = bars()
    monkeypatch.setattr(reversion_module, "atr", lambda *_args: np.asarray([0.01] * 10))
    monkeypatch.setattr(reversion_module, "sma", lambda *_args: np.asarray([1.0] * 10))
    monkeypatch.setattr(reversion_module, "rsi", lambda *_args: np.asarray([50.0] * 10))
    assert strategy.evaluate("EURUSDm", data, 0.00001).reasons == (
        DecisionReason.EXTREME_NOT_CONFIRMED,
    )
    monkeypatch.setattr(
        ExtremeMeanReversionStrategy,
        "_reversion_signal",
        lambda *_args: Signal.BUY,
    )
    buy = strategy.evaluate("EURUSDm", data, 0.00001)
    assert buy.reasons == (DecisionReason.BUY_REVERSION_CONFIRMED,)
    monkeypatch.setattr(
        ExtremeMeanReversionStrategy,
        "_reversion_signal",
        lambda *_args: Signal.SELL,
    )
    sell = strategy.evaluate("EURUSDm", data, 0.00001)
    assert sell.reasons == (DecisionReason.SELL_REVERSION_CONFIRMED,)

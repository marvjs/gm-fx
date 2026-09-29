"""Donchian breakout strategy tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.strategies.donchian import (
    DonchianBreakoutStrategy,
    DonchianFilters,
    DonchianProtection,
    DonchianSettings,
    DonchianStrategyParameters,
    load_donchian_strategy,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal


def settings(**filter_updates: object) -> DonchianSettings:
    filters: dict[str, object] = {
        "max_spread_points": 15,
        "minimum_atr_points": 1.0,
        "maximum_atr_points": 10_000.0,
        "session_start_utc": 0,
        "session_end_utc": 24,
    }
    filters.update(filter_updates)
    return DonchianSettings(
        strategy=DonchianStrategyParameters(
            name="test",
            enabled=True,
            channel_period=3,
            trend_period=4,
            atr_period=3,
            minimum_bars=6,
        ),
        filters=DonchianFilters(**filters),
        protection=DonchianProtection(
            stop_atr_multiple=1.0,
            target_atr_multiple=2.0,
            minimum_reward_risk=1.5,
        ),
    )


def bars(*, final_close: float = 1.005, spread: int = 5) -> list[Bar]:
    start = datetime(2026, 1, 1, 12, tzinfo=UTC)
    closes = [1.000, 1.001, 1.002, 1.003, 1.004, final_close]
    return [
        Bar(
            time=start + timedelta(minutes=index),
            open=close - 0.0002,
            high=close + 0.0004,
            low=close - 0.0004,
            close=close,
            tick_volume=10,
            spread=spread,
            real_volume=0,
        )
        for index, close in enumerate(closes)
    ]


def test_properties_and_invalid_inputs() -> None:
    strategy = DonchianBreakoutStrategy(settings())
    assert strategy.identifier == "donchian_breakout"
    assert strategy.minimum_bars == 6
    with pytest.raises(ValueError, match="bars"):
        strategy.evaluate("EURUSDm", [], 0.00001)
    with pytest.raises(ValueError, match="point"):
        strategy.evaluate("EURUSDm", bars(), 0.0)


def test_insufficient_history_session_and_spread_rejections() -> None:
    strategy = DonchianBreakoutStrategy(settings())
    assert strategy.evaluate("EURUSDm", bars()[:3], 0.00001).reasons == (
        DecisionReason.INSUFFICIENT_HISTORY,
    )
    session_strategy = DonchianBreakoutStrategy(settings(session_start_utc=13, session_end_utc=14))
    assert session_strategy.evaluate("EURUSDm", bars(), 0.00001).reasons == (
        DecisionReason.OUTSIDE_SESSION,
    )
    assert strategy.evaluate("EURUSDm", bars(spread=30), 0.00001).reasons == (
        DecisionReason.SPREAD_TOO_WIDE,
    )


def test_volatility_rejections() -> None:
    assert DonchianBreakoutStrategy(settings(minimum_atr_points=10_000.0)).evaluate(
        "EURUSDm", bars(), 0.00001
    ).reasons == (DecisionReason.VOLATILITY_TOO_LOW,)
    assert DonchianBreakoutStrategy(settings(maximum_atr_points=2.0)).evaluate(
        "EURUSDm", bars(), 0.00001
    ).reasons == (DecisionReason.VOLATILITY_TOO_HIGH,)


def test_buy_and_sell_breakouts_propose_protection() -> None:
    strategy = DonchianBreakoutStrategy(settings())
    buy = strategy.evaluate("EURUSDm", bars(final_close=1.010), 0.00001)
    assert buy.signal is Signal.BUY
    assert buy.reasons == (DecisionReason.BUY_BREAKOUT_CONFIRMED,)
    assert buy.stop_loss is not None
    assert buy.entry is not None
    assert buy.take_profit is not None
    assert buy.stop_loss < buy.entry < buy.take_profit

    descending = bars(final_close=0.990)
    sell = strategy.evaluate("EURUSDm", descending, 0.00001)
    assert sell.signal is Signal.SELL
    assert sell.reasons == (DecisionReason.SELL_BREAKOUT_CONFIRMED,)
    assert sell.stop_loss is not None
    assert sell.entry is not None
    assert sell.take_profit is not None
    assert sell.take_profit < sell.entry < sell.stop_loss


def test_no_breakout_returns_hold() -> None:
    decision = DonchianBreakoutStrategy(settings()).evaluate(
        "EURUSDm", bars(final_close=1.003), 0.00001
    )
    assert decision.signal is Signal.HOLD
    assert decision.reasons == (DecisionReason.BREAKOUT_NOT_CONFIRMED,)


def test_loader_wraps_invalid_configuration(tmp_path: Path) -> None:
    path = tmp_path / "donchian.toml"
    path.write_text("[strategy]\nname='broken'\n", encoding="utf-8")
    with pytest.raises(ConfigurationError, match="invalid"):
        load_donchian_strategy(path)

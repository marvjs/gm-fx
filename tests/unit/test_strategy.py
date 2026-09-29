"""Baseline scalping strategy tests."""

from datetime import UTC, datetime, timedelta

from grandmaster_fx.config.strategy import (
    ProtectionParameters,
    StrategyFilters,
    StrategyParameters,
    StrategySettings,
)
from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies import DecisionReason, Signal, evaluate_baseline


def settings(**filter_updates: object) -> StrategySettings:
    filters = {
        "max_spread_points": 15,
        "minimum_atr_points": 1.0,
        "maximum_atr_points": 10_000.0,
        "minimum_roc_percent": 0.0,
        "buy_rsi_min": 0.0,
        "buy_rsi_max": 100.0,
        "sell_rsi_min": 0.0,
        "sell_rsi_max": 100.0,
        "session_start_utc": 0,
        "session_end_utc": 24,
    }
    filters.update(filter_updates)
    return StrategySettings(
        strategy=StrategyParameters(
            name="test",
            enabled=True,
            fast_ema_period=3,
            slow_ema_period=5,
            rsi_period=3,
            atr_period=3,
            roc_period=2,
            minimum_bars=10,
        ),
        filters=StrategyFilters(**filters),
        protection=ProtectionParameters(
            stop_atr_multiple=1.0, target_atr_multiple=2.0, minimum_reward_risk=1.5
        ),
    )


def bars(*, spread: int = 5, final_bullish: bool = True) -> list[Bar]:
    start = datetime(2026, 9, 28, 12, 0, tzinfo=UTC)
    closes = [1.0000, 1.0005, 1.0010, 1.0015, 1.0020, 1.0025, 1.0030, 1.0035]
    closes.extend([1.0032, 1.0045 if final_bullish else 1.0020])
    result: list[Bar] = []
    for index, close in enumerate(closes):
        open_ = close - 0.0002
        if index == len(closes) - 1 and not final_bullish:
            open_ = close + 0.0002
        result.append(
            Bar(
                time=start + timedelta(minutes=index),
                open=open_,
                high=max(open_, close) + 0.0004,
                low=min(open_, close) - 0.0004,
                close=close,
                tick_volume=10,
                spread=spread,
                real_volume=0,
            )
        )
    return result


def test_wide_spread_returns_hold() -> None:
    decision = evaluate_baseline("EURUSDm", bars(spread=30), 0.00001, settings())
    assert decision.signal is Signal.HOLD
    assert decision.reasons == (DecisionReason.SPREAD_TOO_WIDE,)


def test_insufficient_history_returns_hold() -> None:
    decision = evaluate_baseline("EURUSDm", bars()[:3], 0.00001, settings())
    assert decision.reasons == (DecisionReason.INSUFFICIENT_HISTORY,)


def test_confirmed_buy_proposes_protection_without_order() -> None:
    decision = evaluate_baseline("EURUSDm", bars(), 0.00001, settings())
    assert decision.signal is Signal.BUY
    assert decision.actionable
    assert decision.stop_loss is not None
    assert decision.take_profit is not None
    assert decision.stop_loss < decision.entry < decision.take_profit  # type: ignore[operator]
    assert decision.reward_risk == 2.0


def test_momentum_rejection_is_explainable() -> None:
    decision = evaluate_baseline("EURUSDm", bars(final_bullish=False), 0.00001, settings())
    assert decision.signal is Signal.HOLD
    assert len(decision.reasons) == 1


def test_disabled_strategy_returns_hold() -> None:
    configured = settings()
    disabled = configured.model_copy(
        update={"strategy": configured.strategy.model_copy(update={"enabled": False})}
    )
    decision = evaluate_baseline("EURUSDm", bars(), 0.00001, disabled)
    assert decision.reasons == (DecisionReason.STRATEGY_DISABLED,)


def test_outside_session_returns_hold() -> None:
    decision = evaluate_baseline(
        "EURUSDm", bars(), 0.00001, settings(session_start_utc=13, session_end_utc=14)
    )
    assert decision.reasons == (DecisionReason.OUTSIDE_SESSION,)


def test_low_volatility_returns_hold() -> None:
    decision = evaluate_baseline("EURUSDm", bars(), 0.00001, settings(minimum_atr_points=1_000.0))
    assert decision.reasons == (DecisionReason.VOLATILITY_TOO_LOW,)


def test_high_volatility_returns_hold() -> None:
    decision = evaluate_baseline("EURUSDm", bars(), 0.00001, settings(maximum_atr_points=2.0))
    assert decision.reasons == (DecisionReason.VOLATILITY_TOO_HIGH,)


def test_invalid_inputs_are_rejected() -> None:
    import pytest

    with pytest.raises(ValueError, match="bars"):
        evaluate_baseline("EURUSDm", [], 0.00001, settings())
    with pytest.raises(ValueError, match="point"):
        evaluate_baseline("EURUSDm", bars(), 0.0, settings())

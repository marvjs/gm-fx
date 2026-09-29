"""Transparent EMA-pullback baseline scalping strategy."""

from dataclasses import dataclass

import numpy as np

from grandmaster_fx.config.strategy import StrategySettings
from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.indicators import atr, ema, rate_of_change, rsi
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


@dataclass(frozen=True, slots=True)
class IndicatorState:
    """Latest numerical state used by the baseline decision rules."""

    fast: float
    fast_previous: float
    slow: float
    rsi: float
    atr: float
    roc: float


@dataclass(frozen=True, slots=True)
class SetupResult:
    """Directional setup result before protective prices are calculated."""

    signal: Signal
    reason: DecisionReason


def _hold(
    symbol: str, bars: list[Bar], reason: DecisionReason, *, spread: int | None = None
) -> StrategyDecision:
    return StrategyDecision(
        signal=Signal.HOLD,
        symbol=symbol,
        timestamp=bars[-1].time,
        entry=None,
        stop_loss=None,
        take_profit=None,
        reward_risk=None,
        reasons=(reason,),
        spread_points=spread,
    )


def _preflight_reason(bars: list[Bar], settings: StrategySettings) -> DecisionReason | None:
    """Return the first non-numerical rejection reason."""
    if not settings.strategy.enabled:
        return DecisionReason.STRATEGY_DISABLED
    if len(bars) < settings.strategy.minimum_bars:
        return DecisionReason.INSUFFICIENT_HISTORY
    latest = bars[-1]
    filters = settings.filters
    if not filters.session_start_utc <= latest.time.hour < filters.session_end_utc:
        return DecisionReason.OUTSIDE_SESSION
    if latest.spread > filters.max_spread_points:
        return DecisionReason.SPREAD_TOO_WIDE
    return None


def _indicators(bars: list[Bar], settings: StrategySettings) -> IndicatorState:
    """Calculate the latest indicator state once for all decision rules."""
    close = np.asarray([bar.close for bar in bars], dtype=np.float64)
    high = np.asarray([bar.high for bar in bars], dtype=np.float64)
    low = np.asarray([bar.low for bar in bars], dtype=np.float64)
    fast = ema(close, settings.strategy.fast_ema_period)
    return IndicatorState(
        fast=float(fast[-1]),
        fast_previous=float(fast[-2]),
        slow=float(ema(close, settings.strategy.slow_ema_period)[-1]),
        rsi=float(rsi(close, settings.strategy.rsi_period)[-1]),
        atr=float(atr(high, low, close, settings.strategy.atr_period)[-1]),
        roc=float(rate_of_change(close, settings.strategy.roc_period)[-1]),
    )


def _volatility_reason(
    state: IndicatorState, point: float, settings: StrategySettings
) -> DecisionReason | None:
    """Return a volatility rejection reason when ATR is out of range."""
    atr_points = state.atr / point
    if atr_points < settings.filters.minimum_atr_points:
        return DecisionReason.VOLATILITY_TOO_LOW
    if atr_points > settings.filters.maximum_atr_points:
        return DecisionReason.VOLATILITY_TOO_HIGH
    return None


def _bullish_setup(
    bars: list[Bar], state: IndicatorState, settings: StrategySettings
) -> SetupResult:
    latest, previous = bars[-1], bars[-2]
    if previous.low > state.fast_previous or latest.close <= state.fast:
        return SetupResult(Signal.HOLD, DecisionReason.PULLBACK_NOT_CONFIRMED)
    if latest.close <= latest.open or state.roc < settings.filters.minimum_roc_percent:
        return SetupResult(Signal.HOLD, DecisionReason.MOMENTUM_NOT_CONFIRMED)
    if not settings.filters.buy_rsi_min <= state.rsi <= settings.filters.buy_rsi_max:
        return SetupResult(Signal.HOLD, DecisionReason.RSI_NOT_CONFIRMED)
    return SetupResult(Signal.BUY, DecisionReason.BUY_SETUP_CONFIRMED)


def _bearish_setup(
    bars: list[Bar], state: IndicatorState, settings: StrategySettings
) -> SetupResult:
    latest, previous = bars[-1], bars[-2]
    if previous.high < state.fast_previous or latest.close >= state.fast:
        return SetupResult(Signal.HOLD, DecisionReason.PULLBACK_NOT_CONFIRMED)
    if latest.close >= latest.open or state.roc > -settings.filters.minimum_roc_percent:
        return SetupResult(Signal.HOLD, DecisionReason.MOMENTUM_NOT_CONFIRMED)
    if not settings.filters.sell_rsi_min <= state.rsi <= settings.filters.sell_rsi_max:
        return SetupResult(Signal.HOLD, DecisionReason.RSI_NOT_CONFIRMED)
    return SetupResult(Signal.SELL, DecisionReason.SELL_SETUP_CONFIRMED)


def _setup(bars: list[Bar], state: IndicatorState, settings: StrategySettings) -> SetupResult:
    """Evaluate trend direction and delegate directional confirmation."""
    latest = bars[-1]
    if state.fast > state.slow and latest.close > state.slow:
        return _bullish_setup(bars, state, settings)
    if state.fast < state.slow and latest.close < state.slow:
        return _bearish_setup(bars, state, settings)
    return SetupResult(Signal.HOLD, DecisionReason.TREND_NOT_ALIGNED)


def _protection(
    signal: Signal, entry: float, atr_value: float, settings: StrategySettings
) -> tuple[float, float, float]:
    """Return non-executable stop, target, and reward-risk proposals."""
    stop_distance = atr_value * settings.protection.stop_atr_multiple
    target_distance = atr_value * settings.protection.target_atr_multiple
    reward_risk = target_distance / stop_distance
    if signal is Signal.BUY:
        return entry - stop_distance, entry + target_distance, reward_risk
    return entry + stop_distance, entry - target_distance, reward_risk


def _decision(
    symbol: str,
    bars: list[Bar],
    state: IndicatorState,
    setup: SetupResult,
    settings: StrategySettings,
) -> StrategyDecision:
    """Build the immutable final strategy decision."""
    entry = stop = target = ratio = None
    if setup.signal is not Signal.HOLD:
        entry = bars[-1].close
        stop, target, ratio = _protection(setup.signal, entry, state.atr, settings)
    return StrategyDecision(
        signal=setup.signal,
        symbol=symbol,
        timestamp=bars[-1].time,
        entry=entry,
        stop_loss=stop,
        take_profit=target,
        reward_risk=ratio,
        reasons=(setup.reason,),
        fast_ema=state.fast,
        slow_ema=state.slow,
        rsi=state.rsi,
        atr=state.atr,
        roc=state.roc,
        spread_points=bars[-1].spread,
    )


def evaluate_baseline(
    symbol: str, bars: list[Bar], point: float, settings: StrategySettings
) -> StrategyDecision:
    """Evaluate one completed-candle baseline setup without creating an order."""
    if not bars:
        message = "bars must not be empty"
        raise ValueError(message)
    if point <= 0:
        message = "point must be positive"
        raise ValueError(message)
    rejection = _preflight_reason(bars, settings)
    if rejection is not None:
        return _hold(symbol, bars, rejection, spread=bars[-1].spread)
    state = _indicators(bars, settings)
    rejection = _volatility_reason(state, point, settings)
    if rejection is not None:
        return _hold(symbol, bars, rejection, spread=bars[-1].spread)
    return _decision(symbol, bars, state, _setup(bars, state, settings), settings)

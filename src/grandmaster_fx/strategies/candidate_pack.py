"""Consolidated fixed-risk research strategy candidates."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal, Protocol

import numpy as np
from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from typing import Any

    from grandmaster_fx.domain.market_data import Bar

from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.indicators import atr, ema, rsi, sma
from grandmaster_fx.strategies.common import ProtectionProposal, hold_decision, protected_decision
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


class QualityFilters(Protocol):
    """Fields shared by candidate market-quality filters."""

    max_spread_points: int
    minimum_atr_points: float
    maximum_atr_points: float


class PreparedCandidate(Protocol):
    """Candidate interface required by compatibility evaluation."""

    def prepare(self, bars: list[Bar]) -> CandidateContext: ...

    def evaluate_at(
        self,
        symbol: str,
        bars: list[Bar],
        index: int,
        point: float,
        context: object,
    ) -> StrategyDecision: ...


CandidateKind = Literal[
    "session_range_breakout",
    "fibonacci_pullback",
    "channel_mean_reversion",
    "momentum_continuation",
]


class Protection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stop_atr_multiple: float = Field(gt=0)
    target_atr_multiple: float = Field(gt=0)
    minimum_reward_risk: float = Field(gt=0)


@dataclass(frozen=True, slots=True)
class CandidateContext:
    close: np.ndarray
    high: np.ndarray
    low: np.ndarray
    atr: np.ndarray
    primary: np.ndarray
    secondary: np.ndarray
    tertiary: np.ndarray


class SessionParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    enabled: bool = True
    atr_period: int = Field(gt=1)
    trend_period: int = Field(gt=2)
    minimum_bars: int = Field(gt=2)
    range_start_utc: int = Field(ge=0, le=23)
    range_end_utc: int = Field(ge=1, le=23)
    entry_end_utc: int = Field(ge=2, le=24)


class SessionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_spread_points: int = Field(ge=0)
    breakout_buffer_atr: float = Field(ge=0)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)


class SessionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: SessionParameters
    filters: SessionFilters
    protection: Protection


@dataclass(frozen=True, slots=True)
class SessionRangeBreakoutStrategy:
    settings: SessionSettings

    @property
    def identifier(self) -> str:
        return "session_range_breakout"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def prepare(self, bars: list[Bar]) -> CandidateContext:
        close, high, low = _arrays(bars)
        parameters = self.settings.strategy
        atr_values = atr(high, low, close, parameters.atr_period)
        trend = ema(close, parameters.trend_period)
        upper = np.full(len(bars), np.nan)
        lower = np.full(len(bars), np.nan)
        for index, bar in enumerate(bars):
            day = bar.time.date()
            candidates = [
                item
                for item in bars[:index]
                if item.time.date() == day
                and parameters.range_start_utc <= item.time.hour < parameters.range_end_utc
            ]
            if candidates:
                upper[index] = max(item.high for item in candidates)
                lower[index] = min(item.low for item in candidates)
        return CandidateContext(close, high, low, atr_values, trend, upper, lower)

    def evaluate_at(
        self, symbol: str, bars: list[Bar], index: int, point: float, context: object
    ) -> StrategyDecision:
        context = _require_context(context)
        latest = bars[index]
        parameters = self.settings.strategy
        if not parameters.range_end_utc <= latest.time.hour < parameters.entry_end_utc:
            return hold_decision(symbol, latest, DecisionReason.OUTSIDE_SESSION)
        rejection = _quality(latest, float(context.atr[index]), point, self.settings.filters)
        if rejection is not None:
            return hold_decision(symbol, latest, rejection)
        buffer = context.atr[index] * self.settings.filters.breakout_buffer_atr
        signal = Signal.HOLD
        if (
            latest.close > context.secondary[index] + buffer
            and latest.close > context.primary[index]
        ):
            signal = Signal.BUY
        elif (
            latest.close < context.tertiary[index] - buffer
            and latest.close < context.primary[index]
        ):
            signal = Signal.SELL
        return _finish(symbol, latest, signal, float(context.atr[index]), self.settings.protection)

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        return _compat(self, symbol, bars, point)


class FibonacciParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    enabled: bool = True
    impulse_period: int = Field(gt=3)
    atr_period: int = Field(gt=1)
    trend_period: int = Field(gt=2)
    minimum_bars: int = Field(gt=2)


class FibonacciFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_spread_points: int = Field(ge=0)
    retracement_min: float = Field(gt=0, lt=1)
    retracement_max: float = Field(gt=0, lt=1)
    minimum_impulse_atr: float = Field(gt=0)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)
    session_start_utc: int = Field(ge=0, le=23)
    session_end_utc: int = Field(ge=1, le=24)


class FibonacciSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: FibonacciParameters
    filters: FibonacciFilters
    protection: Protection


@dataclass(frozen=True, slots=True)
class FibonacciPullbackStrategy:
    settings: FibonacciSettings

    @property
    def identifier(self) -> str:
        return "fibonacci_pullback"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def prepare(self, bars: list[Bar]) -> CandidateContext:
        close, high, low = _arrays(bars)
        parameters = self.settings.strategy
        return CandidateContext(
            close,
            high,
            low,
            atr(high, low, close, parameters.atr_period),
            ema(close, parameters.trend_period),
            _rolling(high, parameters.impulse_period, np.max),
            _rolling(low, parameters.impulse_period, np.min),
        )

    def evaluate_at(
        self, symbol: str, bars: list[Bar], index: int, point: float, context: object
    ) -> StrategyDecision:
        context = _require_context(context)
        latest = bars[index]
        filters = self.settings.filters
        if not filters.session_start_utc <= latest.time.hour < filters.session_end_utc:
            return hold_decision(symbol, latest, DecisionReason.OUTSIDE_SESSION)
        atr_value = float(context.atr[index])
        rejection = _quality(latest, atr_value, point, filters)
        if rejection is not None:
            return hold_decision(symbol, latest, rejection)
        high, low = context.secondary[index], context.tertiary[index]
        impulse = high - low
        if impulse < atr_value * filters.minimum_impulse_atr:
            return hold_decision(symbol, latest, DecisionReason.EXTREME_NOT_CONFIRMED)
        bullish = context.primary[index] < latest.close
        ratio = (high - latest.close) / impulse if bullish else (latest.close - low) / impulse
        rejection_candle = latest.close > latest.open if bullish else latest.close < latest.open
        if not filters.retracement_min <= ratio <= filters.retracement_max or not rejection_candle:
            return hold_decision(symbol, latest, DecisionReason.EXHAUSTION_NOT_CONFIRMED)
        signal = Signal.BUY if bullish else Signal.SELL
        return _finish(symbol, latest, signal, atr_value, self.settings.protection)

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        return _compat(self, symbol, bars, point)


class ChannelParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    enabled: bool = True
    channel_period: int = Field(gt=3)
    atr_period: int = Field(gt=1)
    rsi_period: int = Field(gt=1)
    minimum_bars: int = Field(gt=2)


class ChannelFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_spread_points: int = Field(ge=0)
    channel_buffer_atr: float = Field(ge=0)
    buy_rsi_max: float = Field(ge=0, le=100)
    sell_rsi_min: float = Field(ge=0, le=100)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)
    session_start_utc: int = Field(ge=0, le=23)
    session_end_utc: int = Field(ge=1, le=24)


class ChannelSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: ChannelParameters
    filters: ChannelFilters
    protection: Protection


@dataclass(frozen=True, slots=True)
class ChannelMeanReversionStrategy:
    settings: ChannelSettings

    @property
    def identifier(self) -> str:
        return "channel_mean_reversion"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def prepare(self, bars: list[Bar]) -> CandidateContext:
        close, high, low = _arrays(bars)
        parameters = self.settings.strategy
        return CandidateContext(
            close,
            high,
            low,
            atr(high, low, close, parameters.atr_period),
            sma(close, parameters.channel_period),
            rsi(close, parameters.rsi_period),
            np.full(len(bars), np.nan),
        )

    def evaluate_at(
        self, symbol: str, bars: list[Bar], index: int, point: float, context: object
    ) -> StrategyDecision:
        context = _require_context(context)
        latest = bars[index]
        filters = self.settings.filters
        if not filters.session_start_utc <= latest.time.hour < filters.session_end_utc:
            return hold_decision(symbol, latest, DecisionReason.OUTSIDE_SESSION)
        atr_value = float(context.atr[index])
        rejection = _quality(latest, atr_value, point, filters)
        if rejection is not None:
            return hold_decision(symbol, latest, rejection)
        displacement = latest.close - context.primary[index]
        threshold = atr_value * filters.channel_buffer_atr
        signal = Signal.HOLD
        if (
            displacement <= -threshold
            and context.secondary[index] <= filters.buy_rsi_max
            and latest.close > latest.open
        ):
            signal = Signal.BUY
        elif (
            displacement >= threshold
            and context.secondary[index] >= filters.sell_rsi_min
            and latest.close < latest.open
        ):
            signal = Signal.SELL
        return _finish(symbol, latest, signal, atr_value, self.settings.protection)

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        return _compat(self, symbol, bars, point)


class MomentumParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    enabled: bool = True
    fast_period: int = Field(gt=1)
    slow_period: int = Field(gt=2)
    atr_period: int = Field(gt=1)
    roc_period: int = Field(gt=1)
    minimum_bars: int = Field(gt=2)


class MomentumFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_spread_points: int = Field(ge=0)
    minimum_roc_percent: float = Field(gt=0)
    maximum_candle_atr: float = Field(gt=0)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)
    session_start_utc: int = Field(ge=0, le=23)
    session_end_utc: int = Field(ge=1, le=24)


class MomentumSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: MomentumParameters
    filters: MomentumFilters
    protection: Protection


@dataclass(frozen=True, slots=True)
class MomentumContinuationStrategy:
    settings: MomentumSettings

    @property
    def identifier(self) -> str:
        return "momentum_continuation"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def prepare(self, bars: list[Bar]) -> CandidateContext:
        close, high, low = _arrays(bars)
        parameters = self.settings.strategy
        return CandidateContext(
            close,
            high,
            low,
            atr(high, low, close, parameters.atr_period),
            ema(close, parameters.fast_period),
            ema(close, parameters.slow_period),
            _rate_of_change(close, parameters.roc_period),
        )

    def evaluate_at(
        self, symbol: str, bars: list[Bar], index: int, point: float, context: object
    ) -> StrategyDecision:
        context = _require_context(context)
        latest = bars[index]
        filters = self.settings.filters
        if not filters.session_start_utc <= latest.time.hour < filters.session_end_utc:
            return hold_decision(symbol, latest, DecisionReason.OUTSIDE_SESSION)
        atr_value = float(context.atr[index])
        rejection = _quality(latest, atr_value, point, filters)
        if rejection is not None:
            return hold_decision(symbol, latest, rejection)
        if latest.high - latest.low > atr_value * filters.maximum_candle_atr:
            return hold_decision(symbol, latest, DecisionReason.VOLATILITY_TOO_HIGH)
        momentum = float(context.tertiary[index])
        signal = Signal.HOLD
        if (
            context.primary[index] > context.secondary[index]
            and momentum >= filters.minimum_roc_percent
        ):
            signal = Signal.BUY
        elif (
            context.primary[index] < context.secondary[index]
            and momentum <= -filters.minimum_roc_percent
        ):
            signal = Signal.SELL
        return _finish(symbol, latest, signal, atr_value, self.settings.protection)

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        return _compat(self, symbol, bars, point)


def _arrays(bars: list[Bar]) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    return (
        np.asarray([bar.close for bar in bars], dtype=np.float64),
        np.asarray([bar.high for bar in bars], dtype=np.float64),
        np.asarray([bar.low for bar in bars], dtype=np.float64),
    )


def _rate_of_change(values: np.ndarray, period: int) -> np.ndarray:
    """Return percentage rate of change with NaN warm-up values."""
    result = np.full(len(values), np.nan)
    if period >= len(values):
        return result
    previous = values[:-period]
    current = values[period:]
    valid = previous != 0
    calculated = np.full(len(previous), np.nan)
    calculated[valid] = (current[valid] / previous[valid] - 1.0) * 100.0
    result[period:] = calculated
    return result


def _rolling(
    values: np.ndarray,
    period: int,
    function: Callable[[np.ndarray], np.floating[Any]],
) -> np.ndarray:
    result = np.full(len(values), np.nan)
    for index in range(period, len(values)):
        result[index] = function(values[index - period : index])
    return result


def _require_context(context: object) -> CandidateContext:
    if not isinstance(context, CandidateContext):
        message = "candidate strategy requires CandidateContext"
        raise TypeError(message)
    return context


def _quality(
    latest: Bar,
    atr_value: float,
    point: float,
    filters: QualityFilters,
) -> DecisionReason | None:
    if latest.spread > filters.max_spread_points:
        return DecisionReason.SPREAD_TOO_WIDE
    atr_points = atr_value / point
    if atr_points < filters.minimum_atr_points:
        return DecisionReason.VOLATILITY_TOO_LOW
    if atr_points > filters.maximum_atr_points:
        return DecisionReason.VOLATILITY_TOO_HIGH
    return None


def _finish(
    symbol: str, latest: Bar, signal: Signal, atr_value: float, protection: Protection
) -> StrategyDecision:
    if signal is Signal.HOLD:
        return hold_decision(symbol, latest, DecisionReason.TREND_NOT_ALIGNED)
    reason = (
        DecisionReason.BUY_SETUP_CONFIRMED
        if signal is Signal.BUY
        else DecisionReason.SELL_SETUP_CONFIRMED
    )
    return protected_decision(
        symbol,
        latest,
        ProtectionProposal(
            signal=signal,
            reason=reason,
            atr_value=atr_value,
            stop_multiple=protection.stop_atr_multiple,
            target_multiple=protection.target_atr_multiple,
        ),
    )


def _compat(
    strategy: PreparedCandidate,
    symbol: str,
    bars: list[Bar],
    point: float,
) -> StrategyDecision:
    if not bars:
        message = "bars must not be empty"
        raise ValueError(message)
    context = strategy.prepare(bars)
    return strategy.evaluate_at(symbol, bars, len(bars) - 1, point, context)


def _load[SettingsT: BaseModel, StrategyT](
    path: Path,
    settings_type: type[SettingsT],
    strategy_type: Callable[[SettingsT], StrategyT],
) -> StrategyT:
    try:
        with path.open("rb") as stream:
            settings = settings_type.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Candidate strategy configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error
    return strategy_type(settings)


def load_session_range_breakout(path: Path) -> SessionRangeBreakoutStrategy:
    return _load(path, SessionSettings, SessionRangeBreakoutStrategy)


def load_fibonacci_pullback(path: Path) -> FibonacciPullbackStrategy:
    return _load(path, FibonacciSettings, FibonacciPullbackStrategy)


def load_channel_mean_reversion(path: Path) -> ChannelMeanReversionStrategy:
    return _load(path, ChannelSettings, ChannelMeanReversionStrategy)


def load_momentum_continuation(path: Path) -> MomentumContinuationStrategy:
    return _load(path, MomentumSettings, MomentumContinuationStrategy)

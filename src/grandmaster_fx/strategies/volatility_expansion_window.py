"""Expansion within a fixed window after a prior compression event."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.indicators import atr, ema
from grandmaster_fx.strategies.common import (
    ProtectionProposal,
    hold_decision,
    protected_decision,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


class WindowParameters(BaseModel):
    """Fixed structural parameters for the independent window hypothesis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    enabled: bool = True
    range_period: int = Field(gt=2)
    atr_period: int = Field(gt=1)
    compression_period: int = Field(gt=2)
    trend_period: int = Field(gt=2)
    compression_lookback: int = Field(gt=0)
    expansion_window: int = Field(gt=0)
    minimum_bars: int = Field(gt=2)

    @model_validator(mode="after")
    def validate_history(self) -> "WindowParameters":
        required = max(
            self.range_period + 1,
            self.atr_period + self.compression_period,
            self.trend_period,
        )
        if self.minimum_bars < required:
            message = "minimum_bars must cover expansion-window indicator periods"
            raise ValueError(message)
        if self.expansion_window > self.compression_lookback:
            message = "expansion_window cannot exceed compression_lookback"
            raise ValueError(message)
        return self


class WindowFilters(BaseModel):
    """Market-quality and event thresholds."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_spread_points: int = Field(ge=0)
    compression_ratio_max: float = Field(gt=0)
    expansion_ratio_min: float = Field(gt=1)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)
    session_start_utc: int = Field(ge=0, le=23)
    session_end_utc: int = Field(ge=1, le=24)


class WindowProtection(BaseModel):
    """Constant-risk ATR protection."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stop_atr_multiple: float = Field(gt=0)
    target_atr_multiple: float = Field(gt=0)
    minimum_reward_risk: float = Field(gt=0)


class WindowSettings(BaseModel):
    """Validated expansion-window configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: WindowParameters
    filters: WindowFilters
    protection: WindowProtection


@dataclass(frozen=True, slots=True)
class WindowContext:
    """Arrays and event ages precomputed once per historical sample."""

    close: np.ndarray
    atr: np.ndarray
    trend: np.ndarray
    upper: np.ndarray
    lower: np.ndarray
    compression_age: np.ndarray
    compression_atr: np.ndarray


@dataclass(frozen=True, slots=True)
class VolatilityExpansionWindowStrategy:
    """Allow expansion in three completed candles after recent compression."""

    settings: WindowSettings

    @property
    def identifier(self) -> str:
        return "volatility_expansion_window"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def prepare(self, bars: list[Bar]) -> WindowContext:
        """Precompute indicators, prior ranges, and compression-event ages."""
        close = np.asarray([bar.close for bar in bars], dtype=np.float64)
        high = np.asarray([bar.high for bar in bars], dtype=np.float64)
        low = np.asarray([bar.low for bar in bars], dtype=np.float64)
        parameters = self.settings.strategy
        filters = self.settings.filters
        atr_values = atr(high, low, close, parameters.atr_period)
        trend = ema(close, parameters.trend_period)
        length = len(bars)
        upper = np.full(length, np.nan)
        lower = np.full(length, np.nan)
        ages = np.full(length, -1, dtype=np.int64)
        event_atr = np.full(length, np.nan)
        medians = np.full(length, np.nan)
        for index in range(length):
            compression_start = index - parameters.compression_period
            if compression_start >= 0:
                medians[index] = np.nanmedian(atr_values[compression_start:index])
            range_start = index - parameters.range_period
            if range_start >= 0:
                upper[index] = np.max(high[range_start:index])
                lower[index] = np.min(low[range_start:index])
            search_start = max(0, index - parameters.compression_lookback)
            for event_index in range(index - 1, search_start - 1, -1):
                median = medians[event_index]
                if np.isnan(median):
                    continue
                if atr_values[event_index] <= median * filters.compression_ratio_max:
                    ages[index] = index - event_index
                    event_atr[index] = atr_values[event_index]
                    break
        return WindowContext(close, atr_values, trend, upper, lower, ages, event_atr)

    def evaluate_at(  # noqa: PLR0911
        self,
        symbol: str,
        bars: list[Bar],
        index: int,
        point: float,
        context: object,
    ) -> StrategyDecision:
        """Evaluate one completed candle against its recent compression event."""
        if not isinstance(context, WindowContext):
            message = "expansion-window strategy requires WindowContext"
            raise TypeError(message)
        latest = bars[index]
        rejection = self._preflight(bars[: index + 1], latest)
        if rejection is not None:
            return hold_decision(symbol, latest, rejection)
        atr_value = float(context.atr[index])
        volatility = self._volatility_reason(atr_value / point)
        if volatility is not None:
            return hold_decision(symbol, latest, volatility)
        age = int(context.compression_age[index])
        if age < 1:
            return hold_decision(symbol, latest, DecisionReason.COMPRESSION_NOT_CONFIRMED)
        if age > self.settings.strategy.expansion_window:
            return hold_decision(symbol, latest, DecisionReason.EXPANSION_NOT_CONFIRMED)
        threshold = context.compression_atr[index] * self.settings.filters.expansion_ratio_min
        if atr_value < threshold:
            return hold_decision(symbol, latest, DecisionReason.EXPANSION_NOT_CONFIRMED)
        # Emit only at the first threshold crossing for this event.
        if index > 0 and context.atr[index - 1] >= threshold:
            return hold_decision(symbol, latest, DecisionReason.EXPANSION_NOT_CONFIRMED)
        signal = self._signal(latest.close, context, index)
        if signal is Signal.HOLD:
            return hold_decision(symbol, latest, DecisionReason.BREAKOUT_NOT_CONFIRMED)
        reason = (
            DecisionReason.BUY_EXPANSION_CONFIRMED
            if signal is Signal.BUY
            else DecisionReason.SELL_EXPANSION_CONFIRMED
        )
        protection = self.settings.protection
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

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        """Compatibility evaluation for one completed history slice."""
        if not bars:
            message = "bars must not be empty"
            raise ValueError(message)
        context = self.prepare(bars)
        return self.evaluate_at(symbol, bars, len(bars) - 1, point, context)

    def _preflight(self, bars: list[Bar], latest: Bar) -> DecisionReason | None:
        if len(bars) < self.minimum_bars:
            return DecisionReason.INSUFFICIENT_HISTORY
        filters = self.settings.filters
        if not filters.session_start_utc <= latest.time.hour < filters.session_end_utc:
            return DecisionReason.OUTSIDE_SESSION
        if latest.spread > filters.max_spread_points:
            return DecisionReason.SPREAD_TOO_WIDE
        return None

    def _volatility_reason(self, atr_points: float) -> DecisionReason | None:
        filters = self.settings.filters
        if atr_points < filters.minimum_atr_points:
            return DecisionReason.VOLATILITY_TOO_LOW
        if atr_points > filters.maximum_atr_points:
            return DecisionReason.VOLATILITY_TOO_HIGH
        return None

    @staticmethod
    def _signal(close: float, context: WindowContext, index: int) -> Signal:
        if close > context.upper[index] and close > context.trend[index]:
            return Signal.BUY
        if close < context.lower[index] and close < context.trend[index]:
            return Signal.SELL
        return Signal.HOLD


def load_volatility_expansion_window(
    path: Path,
) -> VolatilityExpansionWindowStrategy:
    """Load and validate the fixed expansion-window hypothesis."""
    try:
        with path.open("rb") as stream:
            settings = WindowSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Expansion-window configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error
    return VolatilityExpansionWindowStrategy(settings)

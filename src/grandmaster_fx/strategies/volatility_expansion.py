"""ATR-compression and range-expansion breakout hypothesis."""

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
from grandmaster_fx.strategies.context import ExpansionContext
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


class ExpansionParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    enabled: bool = True
    range_period: int = Field(gt=2)
    atr_period: int = Field(gt=1)
    compression_period: int = Field(gt=2)
    trend_period: int = Field(gt=2)
    minimum_bars: int = Field(gt=2)

    @model_validator(mode="after")
    def validate_history(self) -> "ExpansionParameters":
        required = max(
            self.range_period + 1,
            self.atr_period + self.compression_period,
            self.trend_period,
        )
        if self.minimum_bars < required:
            message = "minimum_bars must cover expansion indicator periods"
            raise ValueError(message)
        return self


class ExpansionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_spread_points: int = Field(ge=0)
    compression_ratio_max: float = Field(gt=0)
    expansion_ratio_min: float = Field(gt=1)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)
    session_start_utc: int = Field(ge=0, le=23)
    session_end_utc: int = Field(ge=1, le=24)


class ExpansionProtection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stop_atr_multiple: float = Field(gt=0)
    target_atr_multiple: float = Field(gt=0)
    minimum_reward_risk: float = Field(gt=0)


class ExpansionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: ExpansionParameters
    filters: ExpansionFilters
    protection: ExpansionProtection


@dataclass(frozen=True, slots=True)
class VolatilityExpansionStrategy:
    """Trade completed-bar breakouts after measured ATR compression."""

    settings: ExpansionSettings

    @property
    def identifier(self) -> str:
        return "volatility_expansion"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def prepare(self, bars: list[Bar]) -> ExpansionContext:
        """Calculate all rolling arrays once for an entire historical sample."""
        close = np.asarray([bar.close for bar in bars], dtype=np.float64)
        high = np.asarray([bar.high for bar in bars], dtype=np.float64)
        low = np.asarray([bar.low for bar in bars], dtype=np.float64)
        parameters = self.settings.strategy
        atr_values = atr(high, low, close, parameters.atr_period)
        trend = ema(close, parameters.trend_period)
        size = len(bars)
        median = np.full(size, np.nan)
        upper = np.full(size, np.nan)
        lower = np.full(size, np.nan)
        for index in range(size):
            compression_start = index - parameters.compression_period
            if compression_start >= 0:
                median[index] = np.nanmedian(atr_values[compression_start:index])
            range_start = index - parameters.range_period
            if range_start >= 0:
                upper[index] = np.max(high[range_start:index])
                lower[index] = np.min(low[range_start:index])
        return ExpansionContext(close, high, low, atr_values, trend, median, upper, lower)

    def evaluate_at(
        self, symbol: str, bars: list[Bar], index: int, point: float, context: object
    ) -> StrategyDecision:
        """Evaluate one candle using precomputed arrays without repeated indicator work."""
        if not isinstance(context, ExpansionContext):
            message = "volatility expansion requires ExpansionContext"
            raise TypeError(message)
        latest = bars[index]
        rejection = self._preflight(bars[: index + 1], latest)
        if rejection is not None:
            return hold_decision(symbol, latest, rejection)
        atr_value = float(context.atr[index])
        reason = self._volatility_reason(atr_value / point)
        if reason is not None:
            return hold_decision(symbol, latest, reason)
        previous_atr = float(context.atr[index - 1])
        compression = float(context.compression_median[index])
        if previous_atr > compression * self.settings.filters.compression_ratio_max:
            return hold_decision(symbol, latest, DecisionReason.COMPRESSION_NOT_CONFIRMED)
        if atr_value < previous_atr * self.settings.filters.expansion_ratio_min:
            return hold_decision(symbol, latest, DecisionReason.EXPANSION_NOT_CONFIRMED)
        signal = Signal.HOLD
        if latest.close > context.previous_upper[index] and latest.close > context.trend[index]:
            signal = Signal.BUY
        elif latest.close < context.previous_lower[index] and latest.close < context.trend[index]:
            signal = Signal.SELL
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
                signal,
                reason,
                atr_value,
                protection.stop_atr_multiple,
                protection.target_atr_multiple,
            ),
        )

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        self._validate_inputs(bars, point)
        latest = bars[-1]
        rejection = self._preflight(bars, latest)
        if rejection is not None:
            return hold_decision(symbol, latest, rejection)
        return self._evaluate_expansion(symbol, bars, point)

    @staticmethod
    def _validate_inputs(bars: list[Bar], point: float) -> None:
        if not bars:
            message = "bars must not be empty"
            raise ValueError(message)
        if point <= 0:
            message = "point must be positive"
            raise ValueError(message)

    def _preflight(self, bars: list[Bar], latest: Bar) -> DecisionReason | None:
        if len(bars) < self.minimum_bars:
            return DecisionReason.INSUFFICIENT_HISTORY
        filters = self.settings.filters
        if not filters.session_start_utc <= latest.time.hour < filters.session_end_utc:
            return DecisionReason.OUTSIDE_SESSION
        if latest.spread > filters.max_spread_points:
            return DecisionReason.SPREAD_TOO_WIDE
        return None

    def _evaluate_expansion(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        latest = bars[-1]
        close = np.asarray([bar.close for bar in bars], dtype=np.float64)
        high = np.asarray([bar.high for bar in bars], dtype=np.float64)
        low = np.asarray([bar.low for bar in bars], dtype=np.float64)
        parameters = self.settings.strategy
        atr_values = atr(high, low, close, parameters.atr_period)
        atr_value = float(atr_values[-1])
        reason = self._volatility_reason(atr_value / point)
        if reason is not None:
            return hold_decision(symbol, latest, reason)
        compression_slice = atr_values[-parameters.compression_period - 1 : -1]
        compression_reference = float(np.nanmedian(compression_slice))
        previous_atr = float(atr_values[-2])
        if previous_atr > compression_reference * self.settings.filters.compression_ratio_max:
            return hold_decision(symbol, latest, DecisionReason.COMPRESSION_NOT_CONFIRMED)
        if atr_value < previous_atr * self.settings.filters.expansion_ratio_min:
            return hold_decision(symbol, latest, DecisionReason.EXPANSION_NOT_CONFIRMED)
        signal = self._breakout_signal(close, high, low)
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

    def _volatility_reason(self, atr_points: float) -> DecisionReason | None:
        filters = self.settings.filters
        if atr_points < filters.minimum_atr_points:
            return DecisionReason.VOLATILITY_TOO_LOW
        if atr_points > filters.maximum_atr_points:
            return DecisionReason.VOLATILITY_TOO_HIGH
        return None

    def _breakout_signal(self, close: np.ndarray, high: np.ndarray, low: np.ndarray) -> Signal:
        period = self.settings.strategy.range_period
        upper = float(np.max(high[-period - 1 : -1]))
        lower = float(np.min(low[-period - 1 : -1]))
        trend = float(ema(close, self.settings.strategy.trend_period)[-1])
        if close[-1] > upper and close[-1] > trend:
            return Signal.BUY
        if close[-1] < lower and close[-1] < trend:
            return Signal.SELL
        return Signal.HOLD


def load_volatility_expansion(path: Path) -> VolatilityExpansionStrategy:
    """Load and validate volatility-expansion settings."""
    try:
        with path.open("rb") as stream:
            settings = ExpansionSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Volatility expansion configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error
    return VolatilityExpansionStrategy(settings)

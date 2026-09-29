"""Donchian breakout research hypothesis."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.indicators import atr, ema
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


class DonchianStrategyParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    enabled: bool = True
    channel_period: int = Field(gt=1)
    trend_period: int = Field(gt=2)
    atr_period: int = Field(gt=1)
    minimum_bars: int = Field(gt=2)

    @model_validator(mode="after")
    def validate_history(self) -> "DonchianStrategyParameters":
        required = max(self.channel_period + 1, self.trend_period, self.atr_period)
        if self.minimum_bars < required:
            message = "minimum_bars must cover Donchian indicator periods"
            raise ValueError(message)
        return self


class DonchianFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_spread_points: int = Field(ge=0)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)
    session_start_utc: int = Field(ge=0, le=23)
    session_end_utc: int = Field(ge=1, le=24)


class DonchianProtection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stop_atr_multiple: float = Field(gt=0)
    target_atr_multiple: float = Field(gt=0)
    minimum_reward_risk: float = Field(gt=0)


class DonchianSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: DonchianStrategyParameters
    filters: DonchianFilters
    protection: DonchianProtection


@dataclass(frozen=True, slots=True)
class DonchianBreakoutStrategy:
    """Research-only trend-aligned channel breakout."""

    settings: DonchianSettings

    @property
    def identifier(self) -> str:
        return "donchian_breakout"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        """Evaluate one completed-bar channel breakout."""
        self._validate_inputs(bars, point)
        latest = bars[-1]
        rejection = self._preflight_reason(bars, latest)
        if rejection is not None:
            return self._hold(symbol, latest, rejection)
        return self._evaluate_channel(symbol, bars, point)

    def _validate_inputs(self, bars: list[Bar], point: float) -> None:
        if not bars:
            message = "bars must not be empty"
            raise ValueError(message)
        if point <= 0:
            message = "point must be positive"
            raise ValueError(message)

    def _preflight_reason(self, bars: list[Bar], latest: Bar) -> DecisionReason | None:
        if len(bars) < self.minimum_bars:
            return DecisionReason.INSUFFICIENT_HISTORY
        filters = self.settings.filters
        if not filters.session_start_utc <= latest.time.hour < filters.session_end_utc:
            return DecisionReason.OUTSIDE_SESSION
        if latest.spread > filters.max_spread_points:
            return DecisionReason.SPREAD_TOO_WIDE
        return None

    def _evaluate_channel(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        latest = bars[-1]
        close = np.asarray([bar.close for bar in bars], dtype=np.float64)
        high = np.asarray([bar.high for bar in bars], dtype=np.float64)
        low = np.asarray([bar.low for bar in bars], dtype=np.float64)
        atr_value = float(atr(high, low, close, self.settings.strategy.atr_period)[-1])
        volatility_reason = self._volatility_reason(atr_value / point)
        if volatility_reason is not None:
            return self._hold(symbol, latest, volatility_reason)
        period = self.settings.strategy.channel_period
        upper = float(np.max(high[-period - 1 : -1]))
        lower = float(np.min(low[-period - 1 : -1]))
        trend = float(ema(close, self.settings.strategy.trend_period)[-1])
        signal = self._breakout_signal(latest.close, upper, lower, trend)
        if signal is Signal.HOLD:
            return self._hold(symbol, latest, DecisionReason.BREAKOUT_NOT_CONFIRMED)
        return self._signal(symbol, latest, signal, atr_value)

    def _volatility_reason(self, atr_points: float) -> DecisionReason | None:
        filters = self.settings.filters
        if atr_points < filters.minimum_atr_points:
            return DecisionReason.VOLATILITY_TOO_LOW
        if atr_points > filters.maximum_atr_points:
            return DecisionReason.VOLATILITY_TOO_HIGH
        return None

    @staticmethod
    def _breakout_signal(close: float, upper: float, lower: float, trend: float) -> Signal:
        if close > upper and close > trend:
            return Signal.BUY
        if close < lower and close < trend:
            return Signal.SELL
        return Signal.HOLD

    def _hold(self, symbol: str, latest: Bar, reason: DecisionReason) -> StrategyDecision:
        return StrategyDecision(
            Signal.HOLD,
            symbol,
            latest.time,
            None,
            None,
            None,
            None,
            (reason,),
            spread_points=latest.spread,
        )

    def _signal(
        self, symbol: str, latest: Bar, signal: Signal, atr_value: float
    ) -> StrategyDecision:
        protection = self.settings.protection
        stop_distance = atr_value * protection.stop_atr_multiple
        target_distance = atr_value * protection.target_atr_multiple
        entry = latest.close
        if signal is Signal.BUY:
            stop, target = entry - stop_distance, entry + target_distance
            reason = DecisionReason.BUY_BREAKOUT_CONFIRMED
        else:
            stop, target = entry + stop_distance, entry - target_distance
            reason = DecisionReason.SELL_BREAKOUT_CONFIRMED
        return StrategyDecision(
            signal,
            symbol,
            latest.time,
            entry,
            stop,
            target,
            target_distance / stop_distance,
            (reason,),
            atr=atr_value,
            spread_points=latest.spread,
        )


def load_donchian_strategy(path: Path) -> DonchianBreakoutStrategy:
    """Load and validate Donchian breakout settings."""
    try:
        with path.open("rb") as stream:
            settings = DonchianSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Donchian strategy configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error
    return DonchianBreakoutStrategy(settings)

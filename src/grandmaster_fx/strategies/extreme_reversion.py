"""Extreme displacement mean-reversion research hypothesis."""

import tomllib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.indicators import atr, rsi, sma
from grandmaster_fx.strategies.common import (
    ProtectionProposal,
    hold_decision,
    protected_decision,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


class ReversionParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    name: str
    enabled: bool = True
    mean_period: int = Field(gt=2)
    atr_period: int = Field(gt=1)
    rsi_period: int = Field(gt=1)
    minimum_bars: int = Field(gt=2)

    @model_validator(mode="after")
    def validate_history(self) -> "ReversionParameters":
        required = max(self.mean_period, self.atr_period, self.rsi_period + 1)
        if self.minimum_bars < required:
            message = "minimum_bars must cover reversion indicator periods"
            raise ValueError(message)
        return self


class ReversionFilters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_spread_points: int = Field(ge=0)
    minimum_displacement_atr: float = Field(gt=0)
    buy_rsi_max: float = Field(ge=0, le=100)
    sell_rsi_min: float = Field(ge=0, le=100)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)
    session_start_utc: int = Field(ge=0, le=23)
    session_end_utc: int = Field(ge=1, le=24)


class ReversionProtection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stop_atr_multiple: float = Field(gt=0)
    target_atr_multiple: float = Field(gt=0)
    minimum_reward_risk: float = Field(gt=0)


class ReversionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    strategy: ReversionParameters
    filters: ReversionFilters
    protection: ReversionProtection


@dataclass(frozen=True, slots=True)
class ExtremeMeanReversionStrategy:
    """Trade exhaustion after displacement from a completed rolling mean."""

    settings: ReversionSettings

    @property
    def identifier(self) -> str:
        return "extreme_mean_reversion"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        self._validate_inputs(bars, point)
        latest = bars[-1]
        rejection = self._preflight(bars, latest)
        if rejection is not None:
            return hold_decision(symbol, latest, rejection)
        return self._evaluate_extreme(symbol, bars, point)

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

    def _evaluate_extreme(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        latest = bars[-1]
        close = np.asarray([bar.close for bar in bars], dtype=np.float64)
        high = np.asarray([bar.high for bar in bars], dtype=np.float64)
        low = np.asarray([bar.low for bar in bars], dtype=np.float64)
        parameters = self.settings.strategy
        atr_value = float(atr(high, low, close, parameters.atr_period)[-1])
        reason = self._volatility_reason(atr_value / point)
        if reason is not None:
            return hold_decision(symbol, latest, reason)
        mean_value = float(sma(close, parameters.mean_period)[-1])
        strength = float(rsi(close, parameters.rsi_period)[-1])
        displacement = (latest.close - mean_value) / atr_value
        signal = self._reversion_signal(latest, displacement, strength)
        if signal is Signal.HOLD:
            reason = self._hold_reason(displacement, strength)
            return hold_decision(symbol, latest, reason)
        reason = (
            DecisionReason.BUY_REVERSION_CONFIRMED
            if signal is Signal.BUY
            else DecisionReason.SELL_REVERSION_CONFIRMED
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

    def _reversion_signal(self, latest: Bar, displacement: float, strength: float) -> Signal:
        filters = self.settings.filters
        bullish_exhaustion = latest.close > latest.open
        bearish_exhaustion = latest.close < latest.open
        if (
            displacement <= -filters.minimum_displacement_atr
            and strength <= filters.buy_rsi_max
            and bullish_exhaustion
        ):
            return Signal.BUY
        if (
            displacement >= filters.minimum_displacement_atr
            and strength >= filters.sell_rsi_min
            and bearish_exhaustion
        ):
            return Signal.SELL
        return Signal.HOLD

    def _hold_reason(self, displacement: float, strength: float) -> DecisionReason:
        filters = self.settings.filters
        extreme = (
            displacement <= -filters.minimum_displacement_atr
            or displacement >= filters.minimum_displacement_atr
        )
        rsi_extreme = strength <= filters.buy_rsi_max or strength >= filters.sell_rsi_min
        if not extreme:
            return DecisionReason.EXTREME_NOT_CONFIRMED
        if not rsi_extreme:
            return DecisionReason.EXTREME_NOT_CONFIRMED
        return DecisionReason.EXHAUSTION_NOT_CONFIRMED


def load_extreme_mean_reversion(path: Path) -> ExtremeMeanReversionStrategy:
    """Load and validate extreme-mean-reversion settings."""
    try:
        with path.open("rb") as stream:
            settings = ReversionSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Extreme mean reversion configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error
    return ExtremeMeanReversionStrategy(settings)

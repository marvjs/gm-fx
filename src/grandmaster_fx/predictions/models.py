"""Prediction-phase immutable domain models."""

from dataclasses import dataclass
from enum import StrEnum

from grandmaster_fx.strategies.models import Signal


class MarketRegime(StrEnum):
    TREND = "trend"
    RANGE = "range"
    COMPRESSION = "compression"
    HIGH_VOLATILITY = "high_volatility"
    UNCERTAIN = "uncertain"


class ConfirmationReason(StrEnum):
    CONFIRMED = "confirmed"
    DISABLED = "disabled"
    HOLD_SIGNAL = "hold_signal"
    INSUFFICIENT_BARS = "insufficient_bars"
    DIRECTION_MISMATCH = "direction_mismatch"
    MOMENTUM_TOO_WEAK = "momentum_too_weak"
    REGIME_MISMATCH = "regime_mismatch"


@dataclass(frozen=True, slots=True)
class RegimeSnapshot:
    regime: MarketRegime
    trend_strength: float
    volatility_ratio: float
    efficiency_ratio: float


@dataclass(frozen=True, slots=True)
class ConfirmationResult:
    confirmed: bool
    signal: Signal
    reason: ConfirmationReason
    fast_average: float | None
    slow_average: float | None
    momentum_percent: float | None


@dataclass(frozen=True, slots=True)
class PredictionAssessment:
    strategy_id: str
    strategy_allowed: bool
    primary_signal: Signal
    regime: RegimeSnapshot
    confirmation: ConfirmationResult

    @property
    def accepted(self) -> bool:
        return (
            self.primary_signal is not Signal.HOLD
            and self.strategy_allowed
            and self.confirmation.confirmed
        )

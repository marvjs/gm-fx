"""Immutable strategy decisions and reason codes."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class Signal(StrEnum):
    """Possible deterministic strategy outcomes."""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class DecisionReason(StrEnum):
    """Machine-readable strategy acceptance and rejection reasons."""

    STRATEGY_DISABLED = "strategy_disabled"
    INSUFFICIENT_HISTORY = "insufficient_history"
    OUTSIDE_SESSION = "outside_session"
    SPREAD_TOO_WIDE = "spread_too_wide"
    VOLATILITY_TOO_LOW = "volatility_too_low"
    VOLATILITY_TOO_HIGH = "volatility_too_high"
    TREND_NOT_ALIGNED = "trend_not_aligned"
    PULLBACK_NOT_CONFIRMED = "pullback_not_confirmed"
    MOMENTUM_NOT_CONFIRMED = "momentum_not_confirmed"
    RSI_NOT_CONFIRMED = "rsi_not_confirmed"
    BUY_SETUP_CONFIRMED = "buy_setup_confirmed"
    SELL_SETUP_CONFIRMED = "sell_setup_confirmed"
    BREAKOUT_NOT_CONFIRMED = "breakout_not_confirmed"
    BUY_BREAKOUT_CONFIRMED = "buy_breakout_confirmed"
    SELL_BREAKOUT_CONFIRMED = "sell_breakout_confirmed"
    COMPRESSION_NOT_CONFIRMED = "compression_not_confirmed"
    EXPANSION_NOT_CONFIRMED = "expansion_not_confirmed"
    BUY_EXPANSION_CONFIRMED = "buy_expansion_confirmed"
    SELL_EXPANSION_CONFIRMED = "sell_expansion_confirmed"
    EXTREME_NOT_CONFIRMED = "extreme_not_confirmed"
    EXHAUSTION_NOT_CONFIRMED = "exhaustion_not_confirmed"
    BUY_REVERSION_CONFIRMED = "buy_reversion_confirmed"
    SELL_REVERSION_CONFIRMED = "sell_reversion_confirmed"


@dataclass(frozen=True, slots=True)
class StrategyDecision:
    """Fully explainable strategy output that is not an executable order."""

    signal: Signal
    symbol: str
    timestamp: datetime
    entry: float | None
    stop_loss: float | None
    take_profit: float | None
    reward_risk: float | None
    reasons: tuple[DecisionReason, ...]
    fast_ema: float | None = None
    slow_ema: float | None = None
    rsi: float | None = None
    atr: float | None = None
    roc: float | None = None
    spread_points: int | None = None

    @property
    def actionable(self) -> bool:
        """Return whether the decision proposes a directional setup."""
        return self.signal in {Signal.BUY, Signal.SELL}

"""Higher-timeframe directional confirmation."""

from statistics import fmean

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.predictions.config import ConfirmationSettings
from grandmaster_fx.predictions.models import (
    ConfirmationReason,
    ConfirmationResult,
    MarketRegime,
)
from grandmaster_fx.strategies.models import Signal


def _result(
    *,
    confirmed: bool,
    signal: Signal,
    reason: ConfirmationReason,
    fast: float | None = None,
    slow: float | None = None,
    momentum: float | None = None,
) -> ConfirmationResult:
    return ConfirmationResult(
        confirmed=confirmed,
        signal=signal,
        reason=reason,
        fast_average=fast,
        slow_average=slow,
        momentum_percent=momentum,
    )


def confirm_higher_timeframe(
    signal: Signal,
    bars: list[Bar],
    regime: MarketRegime,
    settings: ConfirmationSettings,
) -> ConfirmationResult:
    if not settings.enabled:
        return _result(confirmed=True, signal=signal, reason=ConfirmationReason.DISABLED)
    if signal is Signal.HOLD:
        return _result(confirmed=False, signal=signal, reason=ConfirmationReason.HOLD_SIGNAL)
    required = max(settings.slow_period, settings.fast_period + 1)
    if len(bars) < required:
        return _result(
            confirmed=False,
            signal=signal,
            reason=ConfirmationReason.INSUFFICIENT_BARS,
        )
    closes = [item.close for item in bars]
    fast = fmean(closes[-settings.fast_period :])
    slow = fmean(closes[-settings.slow_period :])
    momentum = (closes[-1] / closes[-settings.fast_period] - 1.0) * 100.0
    direction_matches = (signal is Signal.BUY and fast > slow) or (
        signal is Signal.SELL and fast < slow
    )
    if not direction_matches:
        return _result(
            confirmed=False,
            signal=signal,
            reason=ConfirmationReason.DIRECTION_MISMATCH,
            fast=fast,
            slow=slow,
            momentum=momentum,
        )
    momentum_matches = (signal is Signal.BUY and momentum >= settings.minimum_momentum_percent) or (
        signal is Signal.SELL and momentum <= -settings.minimum_momentum_percent
    )
    if not momentum_matches:
        return _result(
            confirmed=False,
            signal=signal,
            reason=ConfirmationReason.MOMENTUM_TOO_WEAK,
            fast=fast,
            slow=slow,
            momentum=momentum,
        )
    if settings.require_regime_alignment and regime not in {
        MarketRegime.TREND,
        MarketRegime.HIGH_VOLATILITY,
    }:
        return _result(
            confirmed=False,
            signal=signal,
            reason=ConfirmationReason.REGIME_MISMATCH,
            fast=fast,
            slow=slow,
            momentum=momentum,
        )
    return _result(
        confirmed=True,
        signal=signal,
        reason=ConfirmationReason.CONFIRMED,
        fast=fast,
        slow=slow,
        momentum=momentum,
    )

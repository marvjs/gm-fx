"""Deterministic market-regime classification."""

from itertools import pairwise
from statistics import fmean

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.predictions.config import RegimeSettings
from grandmaster_fx.predictions.models import MarketRegime, RegimeSnapshot


def classify_regime(bars: list[Bar], settings: RegimeSettings) -> RegimeSnapshot:
    required = max(
        settings.slow_period,
        settings.volatility_lookback,
        settings.atr_period + 1,
    )
    if len(bars) < required:
        return RegimeSnapshot(MarketRegime.UNCERTAIN, 0.0, 1.0, 0.0)
    closes = [item.close for item in bars]
    ranges = [item.high - item.low for item in bars]
    fast = fmean(closes[-settings.fast_period :])
    slow = fmean(closes[-settings.slow_period :])
    current_atr = fmean(ranges[-settings.atr_period :])
    baseline_atr = fmean(ranges[-settings.volatility_lookback :])
    volatility_ratio = current_atr / baseline_atr if baseline_atr > 0 else 1.0
    trend_strength = abs(fast - slow) / current_atr if current_atr > 0 else 0.0
    window = closes[-settings.slow_period :]
    path = sum(abs(right - left) for left, right in pairwise(window))
    efficiency = abs(window[-1] - window[0]) / path if path > 0 else 0.0
    if volatility_ratio >= settings.high_volatility_ratio_threshold:
        regime = MarketRegime.HIGH_VOLATILITY
    elif volatility_ratio <= settings.compression_ratio_threshold:
        regime = MarketRegime.COMPRESSION
    elif (
        trend_strength >= settings.trend_strength_threshold
        and efficiency >= settings.minimum_efficiency_ratio
    ):
        regime = MarketRegime.TREND
    elif efficiency < settings.minimum_efficiency_ratio:
        regime = MarketRegime.RANGE
    else:
        regime = MarketRegime.UNCERTAIN
    return RegimeSnapshot(regime, trend_strength, volatility_ratio, efficiency)

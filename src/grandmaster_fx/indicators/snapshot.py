"""Indicator snapshot construction from validated market bars."""

from dataclasses import dataclass

import numpy as np

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.indicators.core import atr, ema, rate_of_change, rsi, sma


@dataclass(frozen=True, slots=True)
class IndicatorSnapshot:
    """Latest values from the baseline numerical indicator set."""

    close: float
    sma_20: float
    ema_12: float
    ema_26: float
    rsi_14: float
    atr_14: float
    roc_10: float
    spread_points: int


def latest_snapshot(bars: list[Bar]) -> IndicatorSnapshot:
    """Calculate the latest baseline indicator values from completed bars."""
    minimum = 27
    if len(bars) < minimum:
        message = f"At least {minimum} completed bars are required"
        raise ValueError(message)
    close = np.asarray([bar.close for bar in bars], dtype=np.float64)
    high = np.asarray([bar.high for bar in bars], dtype=np.float64)
    low = np.asarray([bar.low for bar in bars], dtype=np.float64)
    return IndicatorSnapshot(
        close=float(close[-1]),
        sma_20=float(sma(close, 20)[-1]),
        ema_12=float(ema(close, 12)[-1]),
        ema_26=float(ema(close, 26)[-1]),
        rsi_14=float(rsi(close, 14)[-1]),
        atr_14=float(atr(high, low, close, 14)[-1]),
        roc_10=float(rate_of_change(close, 10)[-1]),
        spread_points=bars[-1].spread,
    )

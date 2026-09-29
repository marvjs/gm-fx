"""Pure NumPy implementations of the project's numerical indicators."""

from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def _series(values: npt.ArrayLike, *, name: str = "values") -> FloatArray:
    result = np.asarray(values, dtype=np.float64)
    if result.ndim != 1:
        message = f"{name} must be one-dimensional"
        raise ValueError(message)
    if result.size == 0:
        message = f"{name} must not be empty"
        raise ValueError(message)
    if not np.isfinite(result).all():
        message = f"{name} must contain only finite values"
        raise ValueError(message)
    return result


def _period(period: int, size: int) -> None:
    if period < 1:
        message = "period must be positive"
        raise ValueError(message)
    if period > size:
        message = "period cannot exceed series length"
        raise ValueError(message)


def sma(values: npt.ArrayLike, period: int) -> FloatArray:
    """Return a simple moving average with NaN warm-up values."""
    source = _series(values)
    _period(period, source.size)
    result = np.full(source.size, np.nan, dtype=np.float64)
    cumulative = np.cumsum(np.insert(source, 0, 0.0))
    result[period - 1 :] = (cumulative[period:] - cumulative[:-period]) / period
    return result


def ema(values: npt.ArrayLike, period: int) -> FloatArray:
    """Return an EMA seeded by the first period's SMA."""
    source = _series(values)
    _period(period, source.size)
    result = np.full(source.size, np.nan, dtype=np.float64)
    result[period - 1] = source[:period].mean()
    alpha = 2.0 / (period + 1.0)
    for index in range(period, source.size):
        result[index] = alpha * source[index] + (1.0 - alpha) * result[index - 1]
    return result


def true_range(high: npt.ArrayLike, low: npt.ArrayLike, close: npt.ArrayLike) -> FloatArray:
    """Return true range using the previous close after the first candle."""
    highs = _series(high, name="high")
    lows = _series(low, name="low")
    closes = _series(close, name="close")
    if not (highs.size == lows.size == closes.size):
        message = "high, low, and close must have equal lengths"
        raise ValueError(message)
    if np.any(highs < lows):
        message = "high cannot be below low"
        raise ValueError(message)
    previous = np.concatenate(([closes[0]], closes[:-1]))
    result: FloatArray = np.maximum.reduce(
        (highs - lows, np.abs(highs - previous), np.abs(lows - previous))
    )
    return result


def atr(high: npt.ArrayLike, low: npt.ArrayLike, close: npt.ArrayLike, period: int) -> FloatArray:
    """Return Wilder's average true range with NaN warm-up values."""
    ranges = true_range(high, low, close)
    _period(period, ranges.size)
    result = np.full(ranges.size, np.nan, dtype=np.float64)
    result[period - 1] = ranges[:period].mean()
    for index in range(period, ranges.size):
        result[index] = ((period - 1) * result[index - 1] + ranges[index]) / period
    return result


def rsi(values: npt.ArrayLike, period: int = 14) -> FloatArray:
    """Return Wilder RSI with explicit handling for flat and one-sided markets."""
    source = _series(values)
    if period < 1:
        message = "period must be positive"
        raise ValueError(message)
    if source.size <= period:
        message = "series length must exceed RSI period"
        raise ValueError(message)
    changes = np.diff(source)
    gains = np.maximum(changes, 0.0)
    losses = np.maximum(-changes, 0.0)
    result = np.full(source.size, np.nan, dtype=np.float64)
    average_gain = gains[:period].mean()
    average_loss = losses[:period].mean()

    def value(gain: float, loss: float) -> float:
        if gain == 0.0 and loss == 0.0:
            return 50.0
        if loss == 0.0:
            return 100.0
        if gain == 0.0:
            return 0.0
        return 100.0 - 100.0 / (1.0 + gain / loss)

    result[period] = value(average_gain, average_loss)
    for index in range(period + 1, source.size):
        average_gain = ((period - 1) * average_gain + gains[index - 1]) / period
        average_loss = ((period - 1) * average_loss + losses[index - 1]) / period
        result[index] = value(average_gain, average_loss)
    return result


def rate_of_change(values: npt.ArrayLike, period: int) -> FloatArray:
    """Return percentage rate of change over the requested period."""
    source = _series(values)
    _period(period, source.size - 1)
    baseline = source[:-period]
    if np.any(baseline == 0.0):
        message = "rate of change baseline cannot be zero"
        raise ValueError(message)
    result = np.full(source.size, np.nan, dtype=np.float64)
    result[period:] = (source[period:] / baseline - 1.0) * 100.0
    return result


def rolling_volatility(values: npt.ArrayLike, period: int) -> FloatArray:
    """Return population standard deviation over each rolling window."""
    source = _series(values)
    _period(period, source.size)
    result = np.full(source.size, np.nan, dtype=np.float64)
    for index in range(period - 1, source.size):
        result[index] = source[index - period + 1 : index + 1].std(ddof=0)
    return result


def rolling_high(values: npt.ArrayLike, period: int) -> FloatArray:
    """Return rolling maximum values."""
    return _rolling_extreme(values, period, maximum=True)


def rolling_low(values: npt.ArrayLike, period: int) -> FloatArray:
    """Return rolling minimum values."""
    return _rolling_extreme(values, period, maximum=False)


def _rolling_extreme(values: npt.ArrayLike, period: int, *, maximum: bool) -> FloatArray:
    source = _series(values)
    _period(period, source.size)
    result = np.full(source.size, np.nan, dtype=np.float64)
    operation = np.max if maximum else np.min
    for index in range(period - 1, source.size):
        result[index] = operation(source[index - period + 1 : index + 1])
    return result


@dataclass(frozen=True, slots=True)
class CandleMetrics:
    """Vectorized candle body and wick measurements."""

    body: FloatArray
    range: FloatArray
    upper_wick: FloatArray
    lower_wick: FloatArray
    bullish: npt.NDArray[np.bool_]


def candle_metrics(
    open_: npt.ArrayLike, high: npt.ArrayLike, low: npt.ArrayLike, close: npt.ArrayLike
) -> CandleMetrics:
    """Return body, range, wick, and direction measurements."""
    opens = _series(open_, name="open")
    highs = _series(high, name="high")
    lows = _series(low, name="low")
    closes = _series(close, name="close")
    if not (opens.size == highs.size == lows.size == closes.size):
        message = "OHLC arrays must have equal lengths"
        raise ValueError(message)
    if np.any(highs < np.maximum(opens, closes)) or np.any(lows > np.minimum(opens, closes)):
        message = "OHLC values have an invalid candle relationship"
        raise ValueError(message)
    return CandleMetrics(
        body=np.abs(closes - opens),
        range=highs - lows,
        upper_wick=highs - np.maximum(opens, closes),
        lower_wick=np.minimum(opens, closes) - lows,
        bullish=closes > opens,
    )

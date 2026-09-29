"""Numerical indicator tests."""

import numpy as np
import numpy.typing as npt
import pytest
from hypothesis import given
from hypothesis import strategies as st

from grandmaster_fx.indicators import (
    atr,
    candle_metrics,
    ema,
    rate_of_change,
    rolling_high,
    rolling_low,
    rolling_volatility,
    rsi,
    sma,
    true_range,
)


def test_sma_known_values() -> None:
    result = sma([1, 2, 3, 4, 5], 3)
    np.testing.assert_allclose(result[2:], [2, 3, 4])
    assert np.isnan(result[:2]).all()


def test_ema_is_seeded_by_sma() -> None:
    result = ema([1, 2, 3, 4, 5], 3)
    np.testing.assert_allclose(result[2:], [2, 3, 4])


def test_true_range_and_wilder_atr() -> None:
    high = [10, 12, 13, 15]
    low = [8, 9, 11, 12]
    close = [9, 11, 12, 14]
    np.testing.assert_allclose(true_range(high, low, close), [2, 3, 2, 3])
    np.testing.assert_allclose(atr(high, low, close, 3)[2:], [7 / 3, 23 / 9])


def test_rsi_edge_cases() -> None:
    assert rsi(np.arange(1.0, 20.0), 14)[-1] == 100.0
    assert rsi(np.arange(20.0, 1.0, -1.0), 14)[-1] == 0.0
    assert rsi(np.ones(20), 14)[-1] == 50.0


def test_roc_and_rolling_functions() -> None:
    values = [1, 2, 3, 4, 5]
    np.testing.assert_allclose(rate_of_change(values, 2)[2:], [200, 100, 200 / 3])
    np.testing.assert_allclose(rolling_high(values, 3)[2:], [3, 4, 5])
    np.testing.assert_allclose(rolling_low(values, 3)[2:], [1, 2, 3])
    np.testing.assert_allclose(rolling_volatility([1, 1, 1], 3)[-1], 0.0)


def test_candle_metrics() -> None:
    result = candle_metrics([1.0, 2.0], [3.0, 2.5], [0.5, 1.0], [2.0, 1.5])
    np.testing.assert_allclose(result.body, [1.0, 0.5])
    np.testing.assert_allclose(result.upper_wick, [1.0, 0.5])
    np.testing.assert_allclose(result.lower_wick, [0.5, 0.5])
    assert result.bullish.tolist() == [True, False]


@pytest.mark.parametrize(
    "values",
    [[], [[1.0, 2.0]], [1.0, float("nan")], [1.0, float("inf")]],
)
def test_invalid_series_is_rejected(values: npt.ArrayLike) -> None:
    with pytest.raises(ValueError, match="must"):
        sma(values, 1)


@given(
    st.lists(
        st.floats(min_value=0.01, max_value=1_000, allow_nan=False, allow_infinity=False),
        min_size=2,
        max_size=100,
    )
)
def test_sma_stays_inside_each_window(values: list[float]) -> None:
    period = min(5, len(values))
    result = sma(values, period)
    for index in range(period - 1, len(values)):
        window = values[index - period + 1 : index + 1]
        lower = min(window)
        upper = max(window)
        assert result[index] >= lower or np.isclose(result[index], lower)
        assert result[index] <= upper or np.isclose(result[index], upper)


@given(
    st.lists(
        st.floats(min_value=0.01, max_value=1_000, allow_nan=False, allow_infinity=False),
        min_size=15,
        max_size=100,
    )
)
def test_rsi_is_bounded(values: list[float]) -> None:
    result = rsi(values, 14)
    finite = result[np.isfinite(result)]
    assert np.all((finite >= 0.0) & (finite <= 100.0))

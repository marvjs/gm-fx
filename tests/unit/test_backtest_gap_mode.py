"""Regression tests for configured historical-gap modes."""

from datetime import UTC, datetime, timedelta

import pytest

from grandmaster_fx.backtesting.quality import find_history_gaps, validate_history
from grandmaster_fx.config.backtest import load_backtest_settings
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.exceptions import Mt5DataError


def _bar(minutes: int) -> Bar:
    return Bar(
        time=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minutes),
        open=1.0,
        high=1.1,
        low=0.9,
        close=1.0,
        tick_volume=1,
        spread=1,
        real_volume=0,
    )


def test_default_configuration_allows_detected_gaps() -> None:
    settings = load_backtest_settings()
    bars = [_bar(0), _bar(10)]
    assert settings.quality.reject_history_gaps is False
    gaps = validate_history(
        bars,
        Timeframe.M1,
        settings.quality.maximum_gap_multiple,
        reject_gaps=settings.quality.reject_history_gaps,
    )
    assert gaps == find_history_gaps(bars, Timeframe.M1, 3)
    assert gaps[0].missing_intervals == 9


def test_explicit_strict_mode_rejects_the_same_gap() -> None:
    with pytest.raises(Mt5DataError, match="Historical data gap"):
        validate_history([_bar(0), _bar(10)], Timeframe.M1, 3, reject_gaps=True)

"""Historical data quality tests."""

from datetime import UTC, datetime, timedelta

import pytest

from grandmaster_fx.backtesting.quality import history_age_hours, validate_history
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.exceptions import Mt5DataError


def bar(minute: int) -> Bar:
    return Bar(
        datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minute), 1, 1.1, 0.9, 1, 1, 1, 0
    )


def test_valid_history_and_age() -> None:
    data = [bar(0), bar(1), bar(2)]
    validate_history(data, Timeframe.M1, 3)
    assert history_age_hours(data, datetime(2026, 1, 1, 1, 2, tzinfo=UTC)) == 1


def test_gap_is_rejected() -> None:
    with pytest.raises(Mt5DataError, match="gap"):
        validate_history([bar(0), bar(10)], Timeframe.M1, 3)


def test_too_few_bars_are_rejected() -> None:
    with pytest.raises(Mt5DataError, match="At least two"):
        validate_history([bar(0)], Timeframe.M1, 3)


def test_unordered_bars_are_rejected() -> None:
    with pytest.raises(Mt5DataError, match="chronological"):
        validate_history([bar(1), bar(0)], Timeframe.M1, 3)


def test_duplicate_timestamps_are_rejected() -> None:
    with pytest.raises(Mt5DataError, match="unique"):
        validate_history([bar(0), bar(0)], Timeframe.M1, 3)

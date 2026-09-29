"""Historical bar quality checks."""

from dataclasses import dataclass
from datetime import UTC, datetime
from itertools import pairwise

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.exceptions import Mt5DataError

MINIMUM_HISTORY_SIZE = 2


@dataclass(frozen=True, slots=True)
class HistoryGap:
    """One interval larger than the configured gap tolerance."""

    previous: datetime
    current: datetime
    missing_intervals: int


def find_history_gaps(
    bars: list[Bar], timeframe: Timeframe, maximum_gap_multiple: int
) -> tuple[HistoryGap, ...]:
    """Detect large intervals without deciding whether they are fatal."""
    expected_seconds = timeframe.minutes * 60
    gaps: list[HistoryGap] = []
    for previous, current in pairwise(bars):
        elapsed = (current.time - previous.time).total_seconds()
        if elapsed > expected_seconds * maximum_gap_multiple:
            missing = max(1, round(elapsed / expected_seconds) - 1)
            gaps.append(HistoryGap(previous.time, current.time, missing))
    return tuple(gaps)


def validate_history(
    bars: list[Bar],
    timeframe: Timeframe,
    maximum_gap_multiple: int,
    *,
    reject_gaps: bool = True,
) -> tuple[HistoryGap, ...]:
    """Validate ordering and optionally reject detected large intervals."""
    if len(bars) < MINIMUM_HISTORY_SIZE:
        message = "At least two historical bars are required"
        raise Mt5DataError(message)
    if sorted(bars, key=lambda item: item.time) != bars:
        message = "Historical bars must be chronological"
        raise Mt5DataError(message)
    for previous, current in pairwise(bars):
        if current.time <= previous.time:
            message = "Historical bar timestamps must be unique and increasing"
            raise Mt5DataError(message)
    gaps = find_history_gaps(bars, timeframe, maximum_gap_multiple)
    if reject_gaps and gaps:
        message = f"Historical data gap detected before {gaps[0].current.isoformat()}"
        raise Mt5DataError(message)
    return gaps


def history_age_hours(bars: list[Bar], now: datetime | None = None) -> float:
    """Return the age of the latest historical candle in hours."""
    reference = now or datetime.now(UTC)
    return (reference - bars[-1].time).total_seconds() / 3600

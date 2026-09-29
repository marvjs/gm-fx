"""Chronological research split tests."""

from datetime import UTC, datetime, timedelta

import pytest

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.research.splits import anchored_windows, holdout_split


def bars(count: int) -> list[Bar]:
    return [
        Bar(datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=i), 1, 1.1, 0.9, 1, 1, 1, 0)
        for i in range(count)
    ]


def test_holdout_is_chronological() -> None:
    train, test = holdout_split(bars(10), 0.7)
    assert len(train) == 7
    assert len(test) == 3
    assert train[-1].time < test[0].time


def test_invalid_holdout_is_rejected() -> None:
    with pytest.raises(ValueError, match="fraction"):
        holdout_split(bars(10), 0.5)


def test_walk_forward_windows_expand() -> None:
    windows = anchored_windows(1400, 3, 500, 200)
    assert len(windows) == 3
    assert windows[0][1] < windows[1][1] < windows[2][1]


def test_insufficient_walk_forward_history() -> None:
    with pytest.raises(ValueError, match="requires"):
        anchored_windows(500, 3, 500, 200)

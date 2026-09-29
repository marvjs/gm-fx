"""Market data model and export tests."""

import csv
from datetime import UTC
from pathlib import Path

import pytest

from grandmaster_fx.domain.market_data import Bar, Tick, Timeframe, validate_bars
from grandmaster_fx.exceptions import Mt5DataError
from grandmaster_fx.market_data.service import export_bars


def bar(t: int) -> Bar:
    return Bar.from_mapping(
        {
            "time": t,
            "open": 1.0,
            "high": 1.2,
            "low": 0.9,
            "close": 1.1,
            "tick_volume": 10,
            "spread": 5,
            "real_volume": 0,
        }
    )


def test_tick_utc_and_spread() -> None:
    t = Tick.from_mapping({"time_msc": 1000, "bid": 1.1, "ask": 1.2, "last": 0, "volume_real": 2})
    assert t.time.tzinfo is UTC
    assert t.spread == pytest.approx(0.1)


def test_bad_tick() -> None:
    with pytest.raises(Mt5DataError):
        Tick.from_mapping({"time_msc": 1000, "bid": 1.2, "ask": 1.1, "last": 0, "volume_real": 0})


def test_bars_sorted_and_duplicates_rejected() -> None:
    assert [x.time for x in validate_bars([bar(120), bar(60)], Timeframe.M1)] == [
        bar(60).time,
        bar(120).time,
    ]
    with pytest.raises(Mt5DataError):
        validate_bars([bar(60), bar(60)], Timeframe.M1)


def test_bad_ohlc() -> None:
    with pytest.raises(Mt5DataError):
        Bar.from_mapping(
            {
                "time": 1,
                "open": 1,
                "high": 0.5,
                "low": 0.1,
                "close": 1,
                "tick_volume": 1,
                "spread": 1,
                "real_volume": 0,
            }
        )


def test_csv_export(tmp_path: Path) -> None:
    path = export_bars([bar(60)], tmp_path / "bars.csv")
    with path.open(encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 1


def test_bad_export_extension(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="extension"):
        export_bars([bar(60)], tmp_path / "bars.txt")

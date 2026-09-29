"""Validated UTC market-data models."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from grandmaster_fx.exceptions import Mt5DataError


class Timeframe(StrEnum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"

    @property
    def minutes(self) -> int:
        return {"M1": 1, "M5": 5, "M15": 15, "M30": 30, "H1": 60}[self.value]


@dataclass(frozen=True, slots=True)
class Tick:
    time: datetime
    bid: float
    ask: float
    last: float
    volume: float

    @classmethod
    def from_mapping(cls, v: Mapping[str, Any]) -> "Tick":
        try:
            item = cls(
                datetime.fromtimestamp(int(v["time_msc"]) / 1000, UTC),
                float(v["bid"]),
                float(v["ask"]),
                float(v["last"]),
                float(v["volume_real"]),
            )
        except (KeyError, TypeError, ValueError, OSError) as e:
            raise Mt5DataError(f"Invalid tick: {e}") from e
        if item.bid <= 0 or item.ask <= item.bid:
            raise Mt5DataError("Tick must have positive bid and ask greater than bid")
        return item

    @property
    def spread(self) -> float:
        return self.ask - self.bid


@dataclass(frozen=True, slots=True)
class Bar:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    tick_volume: int
    spread: int
    real_volume: int

    @classmethod
    def from_mapping(cls, v: Mapping[str, Any]) -> "Bar":
        try:
            item = cls(
                datetime.fromtimestamp(int(v["time"]), UTC),
                float(v["open"]),
                float(v["high"]),
                float(v["low"]),
                float(v["close"]),
                int(v["tick_volume"]),
                int(v["spread"]),
                int(v["real_volume"]),
            )
        except (KeyError, TypeError, ValueError, OSError) as e:
            raise Mt5DataError(f"Invalid bar: {e}") from e
        if (
            item.low > min(item.open, item.close)
            or item.high < max(item.open, item.close)
            or item.low > item.high
        ):
            raise Mt5DataError("Invalid OHLC relationship")
        return item


def validate_bars(bars: list[Bar], timeframe: Timeframe) -> list[Bar]:
    ordered = sorted(bars, key=lambda x: x.time)
    if len({b.time for b in ordered}) != len(ordered):
        raise Mt5DataError("Duplicate bar timestamps detected")
    return ordered

"""Baseline indicator snapshot tests."""

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.indicators.snapshot import latest_snapshot


def bars(count: int) -> list[Bar]:
    return [
        Bar.from_mapping(
            {
                "time": 60 * index,
                "open": 1.0 + index / 10_000,
                "high": 1.001 + index / 10_000,
                "low": 0.999 + index / 10_000,
                "close": 1.0005 + index / 10_000,
                "tick_volume": 10,
                "spread": 8,
                "real_volume": 0,
            }
        )
        for index in range(30)
    ][:count]


def test_latest_snapshot_returns_finite_values() -> None:
    result = latest_snapshot(bars(30))
    assert result.close > 0
    assert result.ema_12 > 0
    assert 0 <= result.rsi_14 <= 100
    assert result.spread_points == 8

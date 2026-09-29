"""Historical candle cache tests."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.experiments import cache


def test_cache_round_trip(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(cache, "CACHE_DIRECTORY", tmp_path)
    bars = [Bar(datetime(2026, 1, 1, tzinfo=UTC), 1, 1.1, 0.9, 1, 1, 5, 0)]
    path = cache.save_bars("EURUSDm", Timeframe.M1, 1, bars)
    assert path.is_file()
    assert cache.load_bars("EURUSDm", Timeframe.M1, 1) == bars
    assert cache.load_bars("GBPUSDm", Timeframe.M1, 1) is None

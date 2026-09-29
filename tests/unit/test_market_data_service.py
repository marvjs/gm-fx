"""Market-data service orchestration tests."""

from unittest.mock import Mock

import pytest

from grandmaster_fx.domain.market_data import Bar, Tick, Timeframe
from grandmaster_fx.domain.symbols import ForexIdentity, SymbolSnapshot
from grandmaster_fx.market_data.service import MarketDataService, default_export


def symbol(*, selected: bool) -> SymbolSnapshot:
    return SymbolSnapshot(
        name="EURUSDm",
        identity=ForexIdentity("EURUSD", "EUR", "USD"),
        description="Euro vs US Dollar",
        selected=selected,
        visible=True,
        trade_mode=4,
        digits=5,
        point=0.00001,
        spread_points=8,
        spread_float=True,
        tick_size=0.00001,
        tick_value=1.0,
        contract_size=100000.0,
        volume_min=0.01,
        volume_max=200.0,
        volume_step=0.01,
        volume_limit=0.0,
        stops_level=0,
        freeze_level=0,
    )


def bar(timestamp: int) -> Bar:
    return Bar.from_mapping(
        {
            "time": timestamp,
            "open": 1.0,
            "high": 1.2,
            "low": 0.9,
            "close": 1.1,
            "tick_volume": 10,
            "spread": 5,
            "real_volume": 0,
        }
    )


def test_resolve_selects_hidden_symbol() -> None:
    gateway = Mock()
    gateway.symbols.return_value = [symbol(selected=False)]
    service = MarketDataService(gateway, frozenset({"EUR", "USD"}))

    assert service.resolve("EURUSD") == "EURUSDm"
    gateway.select_symbol.assert_called_once_with("EURUSDm")


def test_latest_tick_delegates_to_gateway() -> None:
    gateway = Mock()
    gateway.symbols.return_value = [symbol(selected=True)]
    gateway.tick.return_value = Tick.from_mapping(
        {"time_msc": 1000, "bid": 1.1, "ask": 1.2, "last": 1.15, "volume_real": 1}
    )
    service = MarketDataService(gateway, frozenset({"EUR", "USD"}))

    name, tick = service.latest_tick("EURUSD")

    assert name == "EURUSDm"
    assert tick.bid == 1.1


def test_bars_requests_completed_candles_and_sorts() -> None:
    gateway = Mock()
    gateway.symbols.return_value = [symbol(selected=True)]
    gateway.bars.return_value = [bar(120), bar(60)]
    service = MarketDataService(gateway, frozenset({"EUR", "USD"}))

    name, bars = service.bars("EURUSD", Timeframe.M1, 2)

    assert name == "EURUSDm"
    assert bars == [bar(60), bar(120)]
    gateway.bars.assert_called_once_with("EURUSDm", Timeframe.M1, 2, 1)


def test_bars_can_include_current_candle() -> None:
    gateway = Mock()
    gateway.symbols.return_value = [symbol(selected=True)]
    gateway.bars.return_value = [bar(60)]
    service = MarketDataService(gateway, frozenset({"EUR", "USD"}))

    service.bars("EURUSD", Timeframe.M1, 1, completed_only=False)

    gateway.bars.assert_called_once_with("EURUSDm", Timeframe.M1, 1, 0)


def test_bars_rejects_non_positive_count() -> None:
    service = MarketDataService(Mock(), frozenset({"EUR", "USD"}))
    with pytest.raises(ValueError, match="positive"):
        service.bars("EURUSD", Timeframe.M1, 0)


def test_default_export_uses_normalized_name() -> None:
    path = default_export("eurusd", Timeframe.M5, "csv")
    assert path.parent.as_posix() == "data/exports"
    assert path.name.startswith("EURUSD_M5_")
    assert path.suffix == ".csv"

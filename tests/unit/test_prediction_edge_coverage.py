"""Focused branch coverage for prediction and dashboard components."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.execution.dashboard import _items, _number
from grandmaster_fx.predictions.backtest import required_higher_bar_count
from grandmaster_fx.predictions.config import PredictionSettings, load_prediction_settings
from grandmaster_fx.predictions.confirmation import confirm_higher_timeframe
from grandmaster_fx.predictions.models import ConfirmationReason, MarketRegime
from grandmaster_fx.predictions.regime import classify_regime
from grandmaster_fx.strategies.models import Signal


def make_bars(
    count: int,
    *,
    step: float = 0.0002,
    width: float = 0.001,
) -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(
            start + timedelta(minutes=5 * index),
            1.0 + step * index,
            1.0 + step * index + width,
            1.0 + step * index - width,
            1.0 + step * index,
            1,
            5,
            0,
        )
        for index in range(count)
    ]


def test_dashboard_conversion_helpers_cover_invalid_values() -> None:
    assert _number("1.25") == 1.25
    assert _number("invalid", 7.0) == 7.0
    assert _number(object(), 3.0) == 3.0
    assert _items(("EURUSD", "GBPUSD")) == ["EURUSD", "GBPUSD"]
    assert _items("EURUSD") == []


def test_confirmation_disabled_accepts_directional_signal() -> None:
    settings = load_prediction_settings().confirmation.model_copy(update={"enabled": False})
    result = confirm_higher_timeframe(
        Signal.BUY,
        [],
        MarketRegime.RANGE,
        settings,
    )
    assert result.confirmed
    assert result.reason is ConfirmationReason.DISABLED


def test_confirmation_rejects_insufficient_history() -> None:
    settings = load_prediction_settings().confirmation
    result = confirm_higher_timeframe(
        Signal.SELL,
        make_bars(3),
        MarketRegime.TREND,
        settings,
    )
    assert not result.confirmed
    assert result.reason is ConfirmationReason.INSUFFICIENT_BARS


def test_confirmation_rejects_weak_momentum() -> None:
    settings = load_prediction_settings().confirmation
    result = confirm_higher_timeframe(
        Signal.BUY,
        make_bars(80, step=0.0),
        MarketRegime.TREND,
        settings,
    )
    assert not result.confirmed
    assert result.reason in {
        ConfirmationReason.DIRECTION_MISMATCH,
        ConfirmationReason.MOMENTUM_TOO_WEAK,
    }


def test_regime_classifies_compression_and_high_volatility() -> None:
    settings = load_prediction_settings().regime
    compression = make_bars(120, step=0.0, width=0.0001)
    for index in range(14):
        item = compression[-index - 1]
        compression[-index - 1] = Bar(
            item.time,
            item.open,
            item.close + 0.00001,
            item.close - 0.00001,
            item.close,
            item.tick_volume,
            item.spread,
            item.real_volume,
        )
    assert classify_regime(compression, settings).regime is MarketRegime.COMPRESSION

    volatile = make_bars(120, step=0.0001, width=0.0001)
    for index in range(14):
        item = volatile[-index - 1]
        volatile[-index - 1] = Bar(
            item.time,
            item.open,
            item.close + 0.002,
            item.close - 0.002,
            item.close,
            item.tick_volume,
            item.spread,
            item.real_volume,
        )
    assert classify_regime(volatile, settings).regime is MarketRegime.HIGH_VOLATILITY


def test_prediction_configuration_rejects_reversed_periods() -> None:
    settings = load_prediction_settings().model_dump(mode="python")
    settings["regime"]["fast_period"] = 50
    settings["regime"]["slow_period"] = 20
    with pytest.raises(ValidationError, match="fast period"):
        PredictionSettings.model_validate(settings)


def test_higher_bar_count_has_minimum_floor() -> None:
    assert required_higher_bar_count(10, Timeframe.M1, Timeframe.M15) == 200


def test_prediction_configuration_missing_file_is_wrapped(tmp_path: Path) -> None:
    missing = tmp_path / "missing-predictions.toml"
    with pytest.raises(ConfigurationError, match="Prediction configuration is invalid"):
        load_prediction_settings(missing)

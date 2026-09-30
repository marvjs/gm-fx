"""Regime, strategy selection, and MTF confirmation tests."""

from datetime import UTC, datetime, timedelta

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.predictions.config import load_prediction_settings
from grandmaster_fx.predictions.engine import PredictionEngine
from grandmaster_fx.predictions.models import ConfirmationReason, MarketRegime
from grandmaster_fx.predictions.regime import classify_regime
from grandmaster_fx.strategies.models import Signal


def bars(step: float, count: int = 120, width: float = 0.001) -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    result = []
    for index in range(count):
        close = 1.0 + step * index
        result.append(
            Bar(
                start + timedelta(minutes=5 * index),
                close,
                close + width,
                close - width,
                close,
                1,
                5,
                0,
            )
        )
    return result


def test_trend_regime_and_mtf_confirmation() -> None:
    settings = load_prediction_settings()
    primary = bars(0.0002)
    snapshot = classify_regime(primary, settings.regime)
    assert snapshot.regime is MarketRegime.TREND
    assessment = PredictionEngine(settings).assess(
        "momentum_continuation", Signal.BUY, primary, bars(0.0003)
    )
    assert assessment.accepted
    assert assessment.confirmation.reason is ConfirmationReason.CONFIRMED


def test_wrong_strategy_is_rejected_for_trend() -> None:
    settings = load_prediction_settings()
    assessment = PredictionEngine(settings).assess(
        "channel_mean_reversion", Signal.BUY, bars(0.0002), bars(0.0003)
    )
    assert not assessment.strategy_allowed
    assert not assessment.accepted


def test_opposite_higher_timeframe_rejects_signal() -> None:
    settings = load_prediction_settings()
    assessment = PredictionEngine(settings).assess(
        "momentum_continuation", Signal.BUY, bars(0.0002), bars(-0.0003)
    )
    assert not assessment.accepted
    assert assessment.confirmation.reason is ConfirmationReason.DIRECTION_MISMATCH


def test_insufficient_bars_is_uncertain() -> None:
    settings = load_prediction_settings()
    snapshot = classify_regime(bars(0.0, 10), settings.regime)
    assert snapshot.regime is MarketRegime.UNCERTAIN

"""Prediction-aware backtest tests."""

from datetime import UTC, datetime, timedelta
from unittest.mock import Mock

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.predictions.backtest import (
    PredictionBacktestStrategy,
    required_higher_bar_count,
)
from grandmaster_fx.predictions.models import (
    ConfirmationReason,
    ConfirmationResult,
    MarketRegime,
    PredictionAssessment,
    RegimeSnapshot,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


def bars(count: int, minutes: int) -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(start + timedelta(minutes=index * minutes), 1.0, 1.1, 0.9, 1.0, 1, 5, 0)
        for index in range(count)
    ]


def test_prediction_backtest_accepts_aligned_signal() -> None:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=10)
    strategy.evaluate.return_value = StrategyDecision(
        Signal.BUY,
        "EURUSDm",
        datetime(2026, 1, 1, 2, tzinfo=UTC),
        1.0,
        0.9,
        1.2,
        2.0,
        (DecisionReason.BUY_SETUP_CONFIRMED,),
    )
    engine = Mock()
    engine.settings.confirmation.higher_timeframe = Timeframe.M15
    engine.assess.return_value = PredictionAssessment(
        "momentum_continuation",
        True,
        Signal.BUY,
        RegimeSnapshot(MarketRegime.TREND, 1.0, 1.0, 0.5),
        ConfirmationResult(True, Signal.BUY, ConfirmationReason.CONFIRMED, 1.1, 1.0, 0.2),
    )
    wrapper = PredictionBacktestStrategy("momentum_continuation", strategy, engine, bars(20, 15))
    decision = wrapper.evaluate_at("EURUSDm", bars(30, 5), 20, 0.00001, None)
    assert decision.signal is Signal.BUY
    assert wrapper.report().accepted_signals == 1
    passed_higher = engine.assess.call_args.args[3]
    assert all(item.time + timedelta(minutes=15) <= decision.timestamp for item in passed_higher)


def test_prediction_backtest_rejects_signal() -> None:
    strategy = Mock(identifier="channel_mean_reversion", minimum_bars=10)
    strategy.evaluate.return_value = StrategyDecision(
        Signal.SELL,
        "EURUSDm",
        datetime(2026, 1, 1, 2, tzinfo=UTC),
        1.0,
        1.1,
        0.8,
        2.0,
        (DecisionReason.SELL_SETUP_CONFIRMED,),
    )
    engine = Mock()
    engine.settings.confirmation.higher_timeframe = Timeframe.M15
    engine.assess.return_value = PredictionAssessment(
        "channel_mean_reversion",
        False,
        Signal.SELL,
        RegimeSnapshot(MarketRegime.TREND, 1.0, 1.0, 0.5),
        ConfirmationResult(
            False, Signal.SELL, ConfirmationReason.DIRECTION_MISMATCH, 1.1, 1.0, 0.2
        ),
    )
    wrapper = PredictionBacktestStrategy("channel_mean_reversion", strategy, engine, bars(20, 15))
    decision = wrapper.evaluate_at("EURUSDm", bars(30, 5), 20, 0.00001, None)
    assert decision.signal is Signal.HOLD
    assert wrapper.report().rejection_reasons == {"strategy_not_allowed": 1}


def test_required_higher_bar_count() -> None:
    assert required_higher_bar_count(10000, Timeframe.M5, Timeframe.M15) == 3433

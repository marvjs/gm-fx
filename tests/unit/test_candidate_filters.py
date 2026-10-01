"""Candidate direction and symbol filter tests."""

from datetime import UTC, datetime
from unittest.mock import Mock

from grandmaster_fx.predictions.filters import DirectionalStrategy, TradeDirection
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


def decision(signal: Signal) -> StrategyDecision:
    return StrategyDecision(
        signal,
        "USDJPYm",
        datetime(2026, 1, 1, tzinfo=UTC),
        157.0,
        156.5,
        158.0,
        2.0,
        (DecisionReason.BUY_SETUP_CONFIRMED,),
    )


def test_buy_filter_blocks_sell() -> None:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=10)
    strategy.evaluate.return_value = decision(Signal.SELL)
    filtered = DirectionalStrategy(strategy, TradeDirection.BUY)
    result = filtered.evaluate("USDJPYm", [], 0.001)
    assert result.signal is Signal.HOLD
    assert result.entry is None


def test_buy_filter_preserves_buy() -> None:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=10)
    strategy.evaluate.return_value = decision(Signal.BUY)
    filtered = DirectionalStrategy(strategy, TradeDirection.BUY)
    assert filtered.evaluate("USDJPYm", [], 0.001).signal is Signal.BUY


def test_all_filter_preserves_sell() -> None:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=10)
    strategy.evaluate.return_value = decision(Signal.SELL)
    filtered = DirectionalStrategy(strategy, TradeDirection.ALL)
    assert filtered.evaluate("USDJPYm", [], 0.001).signal is Signal.SELL

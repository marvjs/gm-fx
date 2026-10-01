"""Complete branch coverage for reusable candidate direction filters."""

from datetime import UTC, datetime
from unittest.mock import Mock

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.predictions.filters import DirectionalStrategy, TradeDirection
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision
from grandmaster_fx.strategies.protocol import IndexedResearchStrategy


def make_decision(signal: Signal) -> StrategyDecision:
    return StrategyDecision(
        signal=signal,
        symbol="USDJPYm",
        timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        entry=157.0 if signal is not Signal.HOLD else None,
        stop_loss=156.5 if signal is not Signal.HOLD else None,
        take_profit=158.0 if signal is not Signal.HOLD else None,
        reward_risk=2.0 if signal is not Signal.HOLD else None,
        reasons=(DecisionReason.BUY_SETUP_CONFIRMED,),
    )


def test_trade_direction_allows_expected_signals() -> None:
    assert TradeDirection.ALL.allows(Signal.BUY)
    assert TradeDirection.ALL.allows(Signal.SELL)
    assert TradeDirection.BUY.allows(Signal.BUY)
    assert not TradeDirection.BUY.allows(Signal.SELL)
    assert TradeDirection.SELL.allows(Signal.SELL)
    assert not TradeDirection.SELL.allows(Signal.BUY)


def test_directional_strategy_exposes_wrapped_metadata() -> None:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=60)
    filtered = DirectionalStrategy(strategy, TradeDirection.BUY)
    assert filtered.identifier == "momentum_continuation"
    assert filtered.minimum_bars == 60


def test_prepare_returns_none_for_nonindexed_strategy() -> None:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=60)
    filtered = DirectionalStrategy(strategy, TradeDirection.BUY)
    assert filtered.prepare([]) is None


def test_evaluate_preserves_hold_decision() -> None:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=60)
    strategy.evaluate.return_value = make_decision(Signal.HOLD)
    filtered = DirectionalStrategy(strategy, TradeDirection.BUY)
    result = filtered.evaluate("USDJPYm", [], 0.001)
    assert result.signal is Signal.HOLD


def test_evaluate_at_uses_compatibility_path_and_blocks_sell() -> None:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=60)
    strategy.evaluate.return_value = make_decision(Signal.SELL)
    filtered = DirectionalStrategy(strategy, TradeDirection.BUY)
    bar = Bar(datetime(2026, 1, 1, tzinfo=UTC), 157.0, 157.1, 156.9, 157.0, 1, 5, 0)
    result = filtered.evaluate_at("USDJPYm", [bar], 0, 0.001, None)
    assert result.signal is Signal.HOLD
    strategy.evaluate.assert_called_once_with("USDJPYm", [bar], 0.001)


def test_evaluate_at_uses_indexed_path_and_preserves_buy() -> None:
    strategy = Mock(spec=IndexedResearchStrategy)
    strategy.identifier = "momentum_continuation"
    strategy.minimum_bars = 60
    context = object()
    strategy.prepare.return_value = context
    strategy.evaluate_at.return_value = make_decision(Signal.BUY)
    filtered = DirectionalStrategy(strategy, TradeDirection.BUY)
    bar = Bar(datetime(2026, 1, 1, tzinfo=UTC), 157.0, 157.1, 156.9, 157.0, 1, 5, 0)
    assert filtered.prepare([bar]) is context
    result = filtered.evaluate_at("USDJPYm", [bar], 0, 0.001, context)
    assert result.signal is Signal.BUY
    strategy.evaluate_at.assert_called_once_with("USDJPYm", [bar], 0, 0.001, context)

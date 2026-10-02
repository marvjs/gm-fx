"""Prediction-gated execution worker tests."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.execution.worker import ExecutionWorker
from grandmaster_fx.predictions.models import (
    ConfirmationReason,
    ConfirmationResult,
    MarketRegime,
    PredictionAssessment,
    RegimeSnapshot,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


def make_worker(
    tmp_path: Path,
    accepted: bool,  # noqa: FBT001
) -> tuple[ExecutionWorker, Mock]:
    gateway = Mock()
    gateway.account.return_value = SimpleNamespace(
        trade_mode=SimpleNamespace(name="DEMO"),
        login=123456,
        server="Test-Demo",
        balance=1000.0,
        equity=1000.0,
        profit=0.0,
        margin=0.0,
        margin_free=1000.0,
        trade_allowed=True,
        trade_expert=True,
    )
    gateway.terminal.return_value = SimpleNamespace(
        connected=True,
        trade_allowed=True,
        trade_api_disabled=False,
    )
    gateway.positions.return_value = []
    gateway.pending_orders.return_value = []
    gateway.symbol.return_value = SimpleNamespace(point=0.00001)
    manager = Mock()
    manager.settings.execution.magic = 1
    manager.monitor.return_value = ()
    manager.execute.side_effect = lambda items: tuple(item.symbol for item in items)
    strategy = Mock(identifier="momentum_continuation", minimum_bars=10)
    strategy.evaluate.return_value = StrategyDecision(
        Signal.BUY,
        "EURUSDm",
        datetime(2026, 1, 1, tzinfo=UTC),
        1.1,
        1.09,
        1.12,
        2.0,
        (DecisionReason.BUY_SETUP_CONFIRMED,),
    )
    engine = Mock()
    engine.settings.confirmation.higher_timeframe = Timeframe.M15
    engine.assess.return_value = PredictionAssessment(
        "momentum_continuation",
        accepted,
        Signal.BUY,
        RegimeSnapshot(MarketRegime.TREND, 1.0, 1.0, 0.5),
        ConfirmationResult(
            accepted,
            Signal.BUY,
            ConfirmationReason.CONFIRMED if accepted else ConfirmationReason.DIRECTION_MISMATCH,
            1.1,
            1.0,
            0.2,
        ),
    )
    worker = ExecutionWorker(
        gateway,
        manager,
        strategy,
        Timeframe.M5,
        ("EURUSD",),
        frozenset({"EUR", "USD"}),
        prediction_engine=engine,
        strategy_id="momentum_continuation",
        consumed_path=tmp_path / "consumed.json",
    )
    bar = Bar(datetime(2026, 1, 1, tzinfo=UTC), 1.0, 1.1, 0.9, 1.0, 1, 5, 0)
    worker.service = Mock()
    worker.service.bars.side_effect = [("EURUSDm", [bar] * 120), ("EURUSDm", [bar] * 120)]
    return worker, manager


def test_accepted_prediction_reaches_execution(tmp_path: Path) -> None:
    worker, manager = make_worker(tmp_path, True)
    result = worker.cycle()
    assert result["opened"] == ("EURUSDm",)
    assert result["predictions"][0]["accepted"] is True
    assert manager.execute.call_args.args[0][0].symbol == "EURUSDm"


def test_rejected_prediction_does_not_reach_execution(tmp_path: Path) -> None:
    worker, manager = make_worker(tmp_path, False)
    result = worker.cycle()
    assert result["opened"] == ()
    assert result["predictions"][0]["accepted"] is False
    assert manager.execute.call_args.args[0] == []

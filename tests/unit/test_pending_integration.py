"""Pending-order one-shot integration tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from grandmaster_fx.config.pending_orders import load_pending_order_settings
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.pending.analysis import PendingAnalysisRequest
from grandmaster_fx.pending.models import PendingOrderState
from grandmaster_fx.pending.runtime import (
    PendingPlacementRequest,
    inspect_pending,
    place_paper_pending,
    reconcile_paper_pending,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


def bars() -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(start + timedelta(minutes=5 * index), 100, 101, 99, 100, 1, 1, 0) for index in range(20)
    ]


def strategy(signal: Signal = Signal.BUY) -> Mock:
    value = Mock(identifier="momentum_continuation", minimum_bars=10)
    actionable = signal is not Signal.HOLD
    value.evaluate.return_value = StrategyDecision(
        signal=signal,
        symbol="USDJPYm",
        timestamp=bars()[-1].time,
        entry=100 if actionable else None,
        stop_loss=98 if signal is Signal.BUY else 102 if actionable else None,
        take_profit=104 if signal is Signal.BUY else 96 if actionable else None,
        reward_risk=2 if actionable else None,
        reasons=(
            DecisionReason.BUY_SETUP_CONFIRMED
            if signal is Signal.BUY
            else DecisionReason.TREND_NOT_ALIGNED,
        ),
    )
    return value


def analysis_request(signal: Signal = Signal.BUY) -> PendingAnalysisRequest:
    return PendingAnalysisRequest(
        strategy_id="momentum_continuation",
        strategy=strategy(signal),
        symbol="USDJPYm",
        timeframe=Timeframe.M5,
        bars=bars(),
        point=0.001,
        direction="BUY",
    )


def placement_request(signal: Signal = Signal.BUY) -> PendingPlacementRequest:
    return PendingPlacementRequest(
        analysis=analysis_request(signal),
        settings=load_pending_order_settings(),
    )


def test_inspect_returns_complete_plan() -> None:
    result = inspect_pending(analysis_request(), load_pending_order_settings())
    assert result["planned"] is True
    raw_plan = result["plan"]
    assert isinstance(raw_plan, dict)
    assert raw_plan["order_type"] == "buy_stop"


def test_inspect_hold_returns_explicit_reason() -> None:
    result = inspect_pending(
        analysis_request(Signal.HOLD),
        load_pending_order_settings(),
    )
    assert result["planned"] is False
    assert result["reason"] == "primary_signal_hold"


def test_place_is_one_shot_and_duplicate_safe(tmp_path: Path) -> None:
    path = tmp_path / "pending.json"
    first = place_paper_pending(placement_request(), path)
    second = place_paper_pending(placement_request(), path)
    assert first["placed"] is True
    assert second["placed"] is False
    assert second["reason"] == "existing_order_retained"


def test_reconcile_triggers_and_persists(tmp_path: Path) -> None:
    path = tmp_path / "pending.json"
    placed = place_paper_pending(placement_request(), path)
    trigger = bars()[-1]
    trigger = Bar(trigger.time + timedelta(minutes=5), 102, 103, 99, 102, 1, 1, 0)
    result = reconcile_paper_pending({"USDJPYm": trigger}, path)
    assert placed["placed"] is True
    assert result["triggered"] == 1
    raw_orders = result["orders"]
    assert isinstance(raw_orders, list)
    first_order = raw_orders[0]
    assert isinstance(first_order, dict)
    assert first_order["state"] == PendingOrderState.TRIGGERED.value

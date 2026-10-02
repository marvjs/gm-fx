"""Focused coverage for pending integration lifecycle branches."""

from datetime import UTC, datetime, timedelta
from pathlib import Path

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.pending.models import (
    PendingOrderPlan,
    PendingOrderRecord,
    PendingOrderState,
    PendingOrderType,
)
from grandmaster_fx.pending.service import PendingOrderService
from grandmaster_fx.pending.simulator import evaluate_pending_bar
from grandmaster_fx.pending.store import PendingOrderStore
from grandmaster_fx.strategies.models import Signal

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def plan(
    identity: str = "plan-1",
    *,
    signal: Signal = Signal.BUY,
    order_type: PendingOrderType = PendingOrderType.BUY_STOP,
) -> PendingOrderPlan:
    return PendingOrderPlan(
        identity=identity,
        strategy_id="momentum_continuation",
        symbol="USDJPYm",
        timeframe=Timeframe.M5,
        signal=signal,
        order_type=order_type,
        source_time=NOW,
        trigger_price=100.0,
        stop_loss=99.0 if signal is Signal.BUY else 101.0,
        take_profit=102.0 if signal is Signal.BUY else 98.0,
        maximum_wait_bars=3,
        score=0.8,
    )


def active_record(value: PendingOrderPlan) -> PendingOrderRecord:
    return PendingOrderRecord(
        plan=value,
        state=PendingOrderState.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def test_cancel_active_order_and_preserve_other_records(tmp_path: Path) -> None:
    service = PendingOrderService(PendingOrderStore(tmp_path / "pending.json"))
    first, _created = service.place(plan("first"))
    second_plan = PendingOrderPlan(
        identity="second",
        strategy_id="different_strategy",
        symbol="EURUSDm",
        timeframe=Timeframe.M5,
        signal=Signal.BUY,
        order_type=PendingOrderType.BUY_STOP,
        source_time=NOW,
        trigger_price=1.1,
        stop_loss=1.0,
        take_profit=1.2,
        maximum_wait_bars=3,
        score=0.8,
    )
    service.store.save((first, active_record(second_plan)))

    canceled = service.cancel("first")

    assert canceled is not None
    assert canceled.state is PendingOrderState.CANCELED
    restored = service.list()
    assert restored[0].state is PendingOrderState.CANCELED
    assert restored[1].state is PendingOrderState.ACTIVE


def test_cancel_unknown_identity_returns_none(tmp_path: Path) -> None:
    service = PendingOrderService(PendingOrderStore(tmp_path / "pending.json"))
    service.place(plan())
    assert service.cancel("unknown") is None


def test_replace_persists_updated_record(tmp_path: Path) -> None:
    service = PendingOrderService(PendingOrderStore(tmp_path / "pending.json"))
    placed, _created = service.place(plan())
    triggered = PendingOrderRecord(
        plan=placed.plan,
        state=PendingOrderState.TRIGGERED,
        created_at=placed.created_at,
        updated_at=NOW + timedelta(minutes=5),
        triggered_at=NOW + timedelta(minutes=5),
        triggered_price=100.0,
        reason="trigger_price_reached",
    )

    service.replace(triggered)

    assert service.list()[0].state is PendingOrderState.TRIGGERED


def test_buy_limit_triggers_at_better_open_price() -> None:
    record = active_record(plan(order_type=PendingOrderType.BUY_LIMIT))
    bar = Bar(NOW + timedelta(minutes=5), 99.5, 101.0, 99.0, 100.0, 1, 1, 0)
    result = evaluate_pending_bar(record, bar)
    assert result.record.state is PendingOrderState.TRIGGERED
    assert result.record.triggered_price == 99.5


def test_sell_limit_triggers_at_better_open_price() -> None:
    record = active_record(plan(signal=Signal.SELL, order_type=PendingOrderType.SELL_LIMIT))
    bar = Bar(NOW + timedelta(minutes=5), 100.5, 101.0, 99.0, 100.0, 1, 1, 0)
    result = evaluate_pending_bar(record, bar)
    assert result.record.state is PendingOrderState.TRIGGERED
    assert result.record.triggered_price == 100.5

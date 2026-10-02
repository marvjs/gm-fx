"""Historical pending-order trigger and expiration tests."""

from datetime import UTC, datetime, timedelta

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.pending.models import (
    PendingOrderPlan,
    PendingOrderRecord,
    PendingOrderState,
    PendingOrderType,
)
from grandmaster_fx.pending.simulator import evaluate_pending_bar
from grandmaster_fx.strategies.models import Signal

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def record(order_type: PendingOrderType, signal: Signal) -> PendingOrderRecord:
    plan = PendingOrderPlan(
        identity=f"{order_type.value}-id",
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
    return PendingOrderRecord(plan, PendingOrderState.ACTIVE, NOW, NOW)


def bar(high: float, low: float, opening: float = 99.5) -> Bar:
    return Bar(NOW + timedelta(minutes=5), opening, high, low, 100.0, 1, 1, 0)


def test_buy_stop_triggers() -> None:
    result = evaluate_pending_bar(record(PendingOrderType.BUY_STOP, Signal.BUY), bar(100.2, 99.2))
    assert result.changed
    assert result.record.state is PendingOrderState.TRIGGERED
    assert result.record.triggered_price == 100.0


def test_sell_stop_triggers() -> None:
    result = evaluate_pending_bar(
        record(PendingOrderType.SELL_STOP, Signal.SELL), bar(100.5, 99.8, 100.5)
    )
    assert result.record.state is PendingOrderState.TRIGGERED
    assert result.record.triggered_price == 100.0


def test_pending_order_ages_then_expires() -> None:
    current = record(PendingOrderType.BUY_STOP, Signal.BUY)
    first = evaluate_pending_bar(current, bar(99.9, 99.0)).record
    second = evaluate_pending_bar(first, bar(99.9, 99.0)).record
    third = evaluate_pending_bar(second, bar(99.9, 99.0)).record
    assert first.age_bars == 1
    assert second.age_bars == 2
    assert third.state is PendingOrderState.EXPIRED


def test_terminal_state_is_unchanged() -> None:
    active = record(PendingOrderType.BUY_STOP, Signal.BUY)
    terminal = PendingOrderRecord(
        active.plan,
        PendingOrderState.CANCELED,
        active.created_at,
        active.updated_at,
    )
    result = evaluate_pending_bar(terminal, bar(101.0, 99.0))
    assert not result.changed
    assert result.record is terminal

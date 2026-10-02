"""Deterministic historical and paper pending-order lifecycle evaluation."""

from dataclasses import replace
from datetime import datetime

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.pending.models import (
    PendingEvaluation,
    PendingOrderRecord,
    PendingOrderState,
    PendingOrderType,
)


def _trigger_price(record: PendingOrderRecord, bar: Bar) -> float | None:
    plan = record.plan
    if plan.order_type is PendingOrderType.BUY_STOP and bar.high >= plan.trigger_price:
        return max(plan.trigger_price, bar.open)
    if plan.order_type is PendingOrderType.SELL_STOP and bar.low <= plan.trigger_price:
        return min(plan.trigger_price, bar.open)
    if plan.order_type is PendingOrderType.BUY_LIMIT and bar.low <= plan.trigger_price:
        return min(plan.trigger_price, bar.open)
    if plan.order_type is PendingOrderType.SELL_LIMIT and bar.high >= plan.trigger_price:
        return max(plan.trigger_price, bar.open)
    return None


def evaluate_pending_bar(
    record: PendingOrderRecord,
    bar: Bar,
    evaluated_at: datetime | None = None,
) -> PendingEvaluation:
    """Evaluate one completed bar without lookahead."""
    if record.state is not PendingOrderState.ACTIVE:
        return PendingEvaluation(record=record, changed=False)
    updated_at = evaluated_at or bar.time
    triggered_price = _trigger_price(record, bar)
    if triggered_price is not None:
        triggered = replace(
            record,
            state=PendingOrderState.TRIGGERED,
            updated_at=updated_at,
            triggered_at=bar.time,
            triggered_price=triggered_price,
            reason="trigger_price_reached",
        )
        return PendingEvaluation(record=triggered, changed=True)
    age = record.age_bars + 1
    if age >= record.plan.maximum_wait_bars:
        expired = replace(
            record,
            state=PendingOrderState.EXPIRED,
            updated_at=updated_at,
            age_bars=age,
            reason="maximum_wait_bars_reached",
        )
        return PendingEvaluation(record=expired, changed=True)
    aged = replace(record, updated_at=updated_at, age_bars=age, reason="waiting_for_trigger")
    return PendingEvaluation(record=aged, changed=True)

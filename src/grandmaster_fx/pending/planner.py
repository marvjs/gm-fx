"""Shared deterministic pending-entry planner."""

import hashlib

from grandmaster_fx.config.pending_orders import PendingOrderSettings
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.pending.models import PendingOrderPlan, PendingOrderType
from grandmaster_fx.strategies.models import Signal, StrategyDecision

MINIMUM_COMPLETED_BARS = 2


def _identity(
    strategy_id: str,
    symbol: str,
    timeframe: Timeframe,
    decision: StrategyDecision,
    order_type: PendingOrderType,
    trigger: float,
) -> str:
    payload = "|".join(
        (
            strategy_id,
            symbol,
            timeframe.value,
            decision.signal.value,
            decision.timestamp.isoformat(),
            order_type.value,
            f"{trigger:.10f}",
        )
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def plan_pending_order(
    strategy_id: str,
    symbol: str,
    timeframe: Timeframe,
    decision: StrategyDecision,
    bars: list[Bar],
    settings: PendingOrderSettings,
) -> PendingOrderPlan | None:
    """Convert one accepted directional decision into a broker-neutral stop plan."""
    configuration = settings.pending
    if not configuration.enabled or not configuration.allow_stop:
        return None
    if not decision.actionable or decision.signal is Signal.HOLD:
        return None
    if decision.stop_loss is None or decision.take_profit is None:
        return None
    if len(bars) < MINIMUM_COMPLETED_BARS:
        message = "pending planning requires at least two completed bars"
        raise ValueError(message)
    ranges = [item.high - item.low for item in bars[-14:]]
    average_range = sum(ranges) / len(ranges)
    offset = average_range * configuration.trigger_offset_atr
    latest = bars[-1]
    if decision.signal is Signal.BUY:
        order_type = PendingOrderType.BUY_STOP
        trigger = max(latest.high, decision.entry or latest.close) + offset
        risk = max(trigger - decision.stop_loss, offset)
        stop = decision.stop_loss
        target = max(decision.take_profit, trigger + risk)
    else:
        order_type = PendingOrderType.SELL_STOP
        trigger = min(latest.low, decision.entry or latest.close) - offset
        risk = max(decision.stop_loss - trigger, offset)
        stop = decision.stop_loss
        target = min(decision.take_profit, trigger - risk)
    score = min(1.0, max(0.0, decision.reward_risk or 1.0))
    return PendingOrderPlan(
        identity=_identity(strategy_id, symbol, timeframe, decision, order_type, trigger),
        strategy_id=strategy_id,
        symbol=symbol,
        timeframe=timeframe,
        signal=decision.signal,
        order_type=order_type,
        source_time=decision.timestamp,
        trigger_price=trigger,
        stop_loss=stop,
        take_profit=target,
        maximum_wait_bars=configuration.maximum_wait_bars,
        score=score,
    )

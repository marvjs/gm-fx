"""Shared pending-order planner tests."""

from datetime import UTC, datetime, timedelta

import pytest

from grandmaster_fx.config.pending_orders import PendingOrderSettings
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.pending.models import PendingOrderType
from grandmaster_fx.pending.planner import plan_pending_order
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


def settings() -> PendingOrderSettings:
    return PendingOrderSettings.model_validate(
        {
            "pending": {
                "enabled": True,
                "trigger_offset_atr": 0.1,
                "maximum_wait_bars": 3,
                "replacement_policy": "retain_existing",
                "allow_market": False,
                "allow_stop": True,
                "allow_limit": False,
            }
        }
    )


def bars() -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(start + timedelta(minutes=5 * index), 100, 101, 99, 100, 1, 1, 0) for index in range(20)
    ]


def decision(signal: Signal) -> StrategyDecision:
    return StrategyDecision(
        signal=signal,
        symbol="USDJPYm",
        timestamp=bars()[-1].time,
        entry=100,
        stop_loss=98 if signal is Signal.BUY else 102,
        take_profit=104 if signal is Signal.BUY else 96,
        reward_risk=2,
        reasons=(
            DecisionReason.BUY_SETUP_CONFIRMED
            if signal is Signal.BUY
            else DecisionReason.SELL_SETUP_CONFIRMED,
        ),
    )


def test_buy_decision_creates_buy_stop() -> None:
    plan = plan_pending_order(
        "momentum_continuation", "USDJPYm", Timeframe.M5, decision(Signal.BUY), bars(), settings()
    )
    assert plan is not None
    assert plan.order_type is PendingOrderType.BUY_STOP
    assert plan.trigger_price > bars()[-1].high
    assert plan.stop_loss < plan.trigger_price < plan.take_profit


def test_sell_decision_creates_sell_stop() -> None:
    plan = plan_pending_order(
        "momentum_continuation", "USDJPYm", Timeframe.M5, decision(Signal.SELL), bars(), settings()
    )
    assert plan is not None
    assert plan.order_type is PendingOrderType.SELL_STOP
    assert plan.trigger_price < bars()[-1].low
    assert plan.take_profit < plan.trigger_price < plan.stop_loss


def test_hold_and_disabled_planning_return_none() -> None:
    hold = StrategyDecision(
        Signal.HOLD,
        "USDJPYm",
        bars()[-1].time,
        None,
        None,
        None,
        None,
        (DecisionReason.TREND_NOT_ALIGNED,),
    )
    assert (
        plan_pending_order(
            "momentum_continuation", "USDJPYm", Timeframe.M5, hold, bars(), settings()
        )
        is None
    )
    disabled = settings().model_copy(
        update={"pending": settings().pending.model_copy(update={"enabled": False})}
    )
    assert (
        plan_pending_order(
            "momentum_continuation", "USDJPYm", Timeframe.M5, decision(Signal.BUY), bars(), disabled
        )
        is None
    )


def test_pending_plan_identity_is_deterministic() -> None:
    first = plan_pending_order(
        "momentum_continuation", "USDJPYm", Timeframe.M5, decision(Signal.BUY), bars(), settings()
    )
    second = plan_pending_order(
        "momentum_continuation", "USDJPYm", Timeframe.M5, decision(Signal.BUY), bars(), settings()
    )
    assert first is not None
    assert second is not None
    assert first.identity == second.identity


def test_planner_requires_completed_history() -> None:
    with pytest.raises(ValueError, match="at least two completed bars"):
        plan_pending_order(
            "momentum_continuation",
            "USDJPYm",
            Timeframe.M5,
            decision(Signal.BUY),
            bars()[:1],
            settings(),
        )

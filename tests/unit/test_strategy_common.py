"""Shared strategy decision helper tests."""

from datetime import UTC, datetime

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.common import (
    ProtectionProposal,
    hold_decision,
    protected_decision,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal


def bar() -> Bar:
    """Return one deterministic candle."""
    return Bar(
        time=datetime(2026, 1, 1, tzinfo=UTC),
        open=1.0,
        high=1.1,
        low=0.9,
        close=1.0,
        tick_volume=1,
        spread=5,
        real_volume=0,
    )


def test_hold_decision_has_no_price_proposals() -> None:
    decision = hold_decision(
        "EURUSDm",
        bar(),
        DecisionReason.OUTSIDE_SESSION,
    )
    assert decision.signal is Signal.HOLD
    assert decision.entry is None
    assert decision.stop_loss is None
    assert decision.take_profit is None
    assert decision.reasons == (DecisionReason.OUTSIDE_SESSION,)


def test_protected_buy_and_sell_orientation() -> None:
    buy = protected_decision(
        "EURUSDm",
        bar(),
        ProtectionProposal(
            signal=Signal.BUY,
            reason=DecisionReason.BUY_EXPANSION_CONFIRMED,
            atr_value=0.01,
            stop_multiple=1.0,
            target_multiple=2.0,
        ),
    )
    sell = protected_decision(
        "EURUSDm",
        bar(),
        ProtectionProposal(
            signal=Signal.SELL,
            reason=DecisionReason.SELL_EXPANSION_CONFIRMED,
            atr_value=0.01,
            stop_multiple=1.0,
            target_multiple=2.0,
        ),
    )

    assert buy.entry is not None
    assert buy.stop_loss is not None
    assert buy.take_profit is not None
    assert buy.stop_loss < buy.entry < buy.take_profit

    assert sell.entry is not None
    assert sell.stop_loss is not None
    assert sell.take_profit is not None
    assert sell.take_profit < sell.entry < sell.stop_loss

    assert buy.reward_risk == 2.0
    assert sell.reward_risk == 2.0

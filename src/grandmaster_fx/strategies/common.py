"""Shared helpers for fixed-parameter research strategies."""

from dataclasses import dataclass

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


@dataclass(frozen=True, slots=True)
class ProtectionProposal:
    """ATR-derived protection inputs for one directional decision."""

    signal: Signal
    reason: DecisionReason
    atr_value: float
    stop_multiple: float
    target_multiple: float


def hold_decision(symbol: str, latest: Bar, reason: DecisionReason) -> StrategyDecision:
    """Return one non-actionable immutable strategy decision."""
    return StrategyDecision(
        signal=Signal.HOLD,
        symbol=symbol,
        timestamp=latest.time,
        entry=None,
        stop_loss=None,
        take_profit=None,
        reward_risk=None,
        reasons=(reason,),
        spread_points=latest.spread,
    )


def protected_decision(
    symbol: str,
    latest: Bar,
    proposal: ProtectionProposal,
) -> StrategyDecision:
    """Return one directional decision with ATR-derived protection."""
    entry = latest.close
    stop_distance = proposal.atr_value * proposal.stop_multiple
    target_distance = proposal.atr_value * proposal.target_multiple
    if proposal.signal is Signal.BUY:
        stop_loss = entry - stop_distance
        take_profit = entry + target_distance
    else:
        stop_loss = entry + stop_distance
        take_profit = entry - target_distance
    return StrategyDecision(
        signal=proposal.signal,
        symbol=symbol,
        timestamp=latest.time,
        entry=entry,
        stop_loss=stop_loss,
        take_profit=take_profit,
        reward_risk=target_distance / stop_distance,
        reasons=(proposal.reason,),
        atr=proposal.atr_value,
        spread_points=latest.spread,
    )

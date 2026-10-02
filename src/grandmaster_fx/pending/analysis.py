"""Shared pending-order analysis input and gate outcome."""

from dataclasses import dataclass

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.predictions.engine import PredictionEngine
from grandmaster_fx.strategies.models import Signal, StrategyDecision
from grandmaster_fx.strategies.protocol import ResearchStrategy


@dataclass(frozen=True, slots=True)
class PendingAnalysisRequest:
    """Complete inputs for one pending analysis pass."""

    strategy_id: str
    strategy: ResearchStrategy
    symbol: str
    timeframe: Timeframe
    bars: list[Bar]
    point: float
    direction: str
    prediction_engine: PredictionEngine | None = None
    higher_bars: list[Bar] | None = None


@dataclass(frozen=True, slots=True)
class PendingAnalysis:
    """Primary decision plus direction and optional prediction-gate outcome."""

    primary: StrategyDecision
    filtered: StrategyDecision
    direction_allowed: bool
    accepted: bool
    reason: str
    regime: str | None = None
    strategy_allowed: bool | None = None
    confirmation: bool | None = None
    confirmation_reason: str | None = None


def analyze_pending(request: PendingAnalysisRequest) -> PendingAnalysis:
    """Evaluate the raw strategy once and apply shared direction and prediction gates."""
    primary = request.strategy.evaluate(request.symbol, request.bars, request.point)
    direction_allowed = request.direction in {"ALL", primary.signal.value}
    filtered = primary
    if primary.actionable and not direction_allowed:
        filtered = StrategyDecision(
            signal=Signal.HOLD,
            symbol=primary.symbol,
            timestamp=primary.timestamp,
            entry=None,
            stop_loss=None,
            take_profit=None,
            reward_risk=None,
            reasons=primary.reasons,
        )
    if not primary.actionable:
        return PendingAnalysis(
            primary=primary,
            filtered=filtered,
            direction_allowed=direction_allowed,
            accepted=False,
            reason="primary_signal_hold",
        )
    if not direction_allowed:
        return PendingAnalysis(
            primary=primary,
            filtered=filtered,
            direction_allowed=False,
            accepted=False,
            reason="direction_not_allowed",
        )
    if request.prediction_engine is None:
        return PendingAnalysis(
            primary=primary,
            filtered=filtered,
            direction_allowed=True,
            accepted=True,
            reason="accepted_without_prediction_gates",
        )
    if request.higher_bars is None:
        message = "prediction-gated pending analysis requires higher-timeframe bars"
        raise ValueError(message)
    assessment = request.prediction_engine.assess(
        request.strategy_id,
        primary.signal,
        request.bars,
        request.higher_bars,
    )
    if not assessment.strategy_allowed:
        reason = "strategy_not_allowed"
    elif not assessment.confirmation.confirmed:
        reason = assessment.confirmation.reason.value
    else:
        reason = "prediction_gates_passed"
    return PendingAnalysis(
        primary=primary,
        filtered=filtered,
        direction_allowed=True,
        accepted=assessment.accepted,
        reason=reason,
        regime=assessment.regime.regime.value,
        strategy_allowed=assessment.strategy_allowed,
        confirmation=assessment.confirmation.confirmed,
        confirmation_reason=assessment.confirmation.reason.value,
    )

"""Prediction-gate parity for one-shot pending analysis."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from grandmaster_fx.config.pending_orders import load_pending_order_settings
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.pending.analysis import PendingAnalysisRequest
from grandmaster_fx.pending.runtime import (
    PendingPlacementRequest,
    inspect_pending,
    place_paper_pending,
)
from grandmaster_fx.predictions.models import (
    ConfirmationReason,
    ConfirmationResult,
    MarketRegime,
    PredictionAssessment,
    RegimeSnapshot,
)
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


def bars() -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(start + timedelta(minutes=5 * index), 100, 101, 99, 100, 1, 1, 0) for index in range(80)
    ]


def strategy(signal: Signal) -> Mock:
    value = Mock(identifier="momentum_continuation", minimum_bars=60)
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
            else DecisionReason.SELL_SETUP_CONFIRMED
            if signal is Signal.SELL
            else DecisionReason.TREND_NOT_ALIGNED,
        ),
    )
    return value


def request(
    signal: Signal, direction: str = "BUY", engine: Mock | None = None
) -> PendingAnalysisRequest:
    return PendingAnalysisRequest(
        strategy_id="momentum_continuation",
        strategy=strategy(signal),
        symbol="USDJPYm",
        timeframe=Timeframe.M5,
        bars=bars(),
        point=0.001,
        direction=direction,
        prediction_engine=engine,
        higher_bars=bars() if engine is not None else None,
    )


def assessment(
    *, accepted: bool, allowed: bool = True, confirmed: bool = True
) -> PredictionAssessment:
    if accepted:
        allowed = True
        confirmed = True
    return PredictionAssessment(
        strategy_id="momentum_continuation",
        primary_signal=Signal.BUY,
        regime=RegimeSnapshot(MarketRegime.TREND, 1.0, 1.0, 1.0),
        strategy_allowed=allowed,
        confirmation=ConfirmationResult(
            signal=Signal.BUY,
            confirmed=confirmed,
            reason=ConfirmationReason.CONFIRMED
            if confirmed
            else ConfirmationReason.DIRECTION_MISMATCH,
            fast_average=101.0,
            slow_average=100.0,
            momentum_percent=0.1,
        ),
    )


def test_direction_block_reports_primary_and_filtered_signal() -> None:
    result = inspect_pending(request(Signal.SELL), load_pending_order_settings())
    assert result["primary_signal"] == "SELL"
    assert result["filtered_signal"] == "HOLD"
    assert result["direction_allowed"] is False
    assert result["reason"] == "direction_not_allowed"


def test_prediction_gates_create_plan_when_accepted() -> None:
    engine = Mock()
    engine.assess.return_value = assessment(accepted=True)
    result = inspect_pending(request(Signal.BUY, engine=engine), load_pending_order_settings())
    assert result["accepted"] is True
    assert result["planned"] is True
    assert result["reason"] == "pending_plan_created"


def test_prediction_strategy_rejection_is_explicit() -> None:
    engine = Mock()
    engine.assess.return_value = assessment(accepted=False, allowed=False)
    result = inspect_pending(request(Signal.BUY, engine=engine), load_pending_order_settings())
    assert result["planned"] is False
    assert result["reason"] == "strategy_not_allowed"


def test_prediction_confirmation_rejection_is_explicit() -> None:
    engine = Mock()
    engine.assess.return_value = assessment(accepted=False, confirmed=False)
    result = inspect_pending(request(Signal.BUY, engine=engine), load_pending_order_settings())
    assert result["planned"] is False
    assert result["reason"] == "direction_mismatch"


def test_paper_placement_persists_only_accepted_plan(tmp_path: Path) -> None:
    engine = Mock()
    engine.assess.return_value = assessment(accepted=True)
    placement = PendingPlacementRequest(
        analysis=request(Signal.BUY, engine=engine),
        settings=load_pending_order_settings(),
    )
    result = place_paper_pending(placement, tmp_path / "pending.json")
    assert result["placed"] is True

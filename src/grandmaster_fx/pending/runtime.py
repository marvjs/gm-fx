"""One-shot pending-order inspection, paper placement, and reconciliation."""

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from grandmaster_fx.config.pending_orders import PendingOrderSettings
from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.pending.analysis import PendingAnalysisRequest, analyze_pending
from grandmaster_fx.pending.models import PendingOrderRecord, PendingOrderState
from grandmaster_fx.pending.planner import plan_pending_order
from grandmaster_fx.pending.service import PendingOrderService
from grandmaster_fx.pending.simulator import evaluate_pending_bar
from grandmaster_fx.pending.store import PendingOrderStore
from grandmaster_fx.strategies.models import StrategyDecision

DEFAULT_PAPER_PENDING_PATH = Path("data/paper/pending_orders.json")


class PendingStrategy(Protocol):
    """Minimum strategy interface needed by one-shot pending analysis."""

    @property
    def identifier(self) -> str: ...

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision: ...


@dataclass(frozen=True, slots=True)
class PendingPlacementRequest:
    """Inputs shared by one-shot paper pending placement."""

    analysis: PendingAnalysisRequest
    settings: PendingOrderSettings


def record_payload(record: PendingOrderRecord) -> dict[str, object]:
    """Return a JSON-compatible pending-order record."""
    payload = asdict(record)
    plan = payload["plan"]
    if not isinstance(plan, dict):
        message = "pending record plan serialization failed"
        raise TypeError(message)
    plan["timeframe"] = record.plan.timeframe.value
    plan["signal"] = record.plan.signal.value
    plan["order_type"] = record.plan.order_type.value
    plan["source_time"] = record.plan.source_time.isoformat()
    payload["state"] = record.state.value
    payload["created_at"] = record.created_at.isoformat()
    payload["updated_at"] = record.updated_at.isoformat()
    payload["triggered_at"] = (
        record.triggered_at.isoformat() if record.triggered_at is not None else None
    )
    return payload


def inspect_pending(
    request: PendingAnalysisRequest,
    settings: PendingOrderSettings,
) -> dict[str, object]:
    """Evaluate once and return gate diagnostics plus an optional pending plan."""
    analysis = analyze_pending(request)
    plan = (
        plan_pending_order(
            request.strategy_id,
            request.symbol,
            request.timeframe,
            analysis.filtered,
            request.bars,
            settings,
        )
        if analysis.accepted
        else None
    )
    result: dict[str, object] = {
        "symbol": request.symbol,
        "strategy_id": request.strategy_id,
        "timeframe": request.timeframe.value,
        "primary_signal": analysis.primary.signal.value,
        "filtered_signal": analysis.filtered.signal.value,
        "source_time": analysis.primary.timestamp.isoformat(),
        "decision_reasons": [item.value for item in analysis.primary.reasons],
        "direction_allowed": analysis.direction_allowed,
        "predictions_enabled": request.prediction_engine is not None,
        "regime": analysis.regime,
        "strategy_allowed": analysis.strategy_allowed,
        "confirmation": analysis.confirmation,
        "confirmation_reason": analysis.confirmation_reason,
        "accepted": analysis.accepted,
        "planned": plan is not None,
        "reason": analysis.reason if plan is None else "pending_plan_created",
    }
    if plan is not None:
        result["plan"] = {
            "identity": plan.identity,
            "order_type": plan.order_type.value,
            "trigger_price": plan.trigger_price,
            "stop_loss": plan.stop_loss,
            "take_profit": plan.take_profit,
            "maximum_wait_bars": plan.maximum_wait_bars,
            "score": plan.score,
        }
    return result


def place_paper_pending(
    request: PendingPlacementRequest,
    path: Path = DEFAULT_PAPER_PENDING_PATH,
) -> dict[str, object]:
    """Analyze once, persist an accepted paper pending order, and return immediately."""
    analysis = analyze_pending(request.analysis)
    if not analysis.accepted:
        return {
            "placed": False,
            "reason": analysis.reason,
            "primary_signal": analysis.primary.signal.value,
            "filtered_signal": analysis.filtered.signal.value,
            "direction_allowed": analysis.direction_allowed,
            "regime": analysis.regime,
            "strategy_allowed": analysis.strategy_allowed,
            "confirmation": analysis.confirmation,
            "confirmation_reason": analysis.confirmation_reason,
            "decision_reasons": [item.value for item in analysis.primary.reasons],
        }
    plan = plan_pending_order(
        request.analysis.strategy_id,
        request.analysis.symbol,
        request.analysis.timeframe,
        analysis.filtered,
        request.analysis.bars,
        request.settings,
    )
    if plan is None:
        return {
            "placed": False,
            "reason": "no_actionable_pending_setup",
            "primary_signal": analysis.primary.signal.value,
            "filtered_signal": analysis.filtered.signal.value,
        }
    record, created = PendingOrderService(PendingOrderStore(path)).place(plan)
    return {
        "placed": created,
        "reason": "paper_pending_order_placed" if created else "existing_order_retained",
        "record": record_payload(record),
    }


def reconcile_paper_pending(
    completed_bars: dict[str, Bar],
    path: Path = DEFAULT_PAPER_PENDING_PATH,
) -> dict[str, object]:
    """Evaluate each active paper order against one newly completed bar."""
    service = PendingOrderService(PendingOrderStore(path))
    records = service.list()
    updated: list[PendingOrderRecord] = []
    changed: list[dict[str, object]] = []
    for record in records:
        bar = completed_bars.get(record.plan.symbol)
        if bar is None or record.state is not PendingOrderState.ACTIVE:
            updated.append(record)
            continue
        evaluation = evaluate_pending_bar(record, bar)
        updated.append(evaluation.record)
        if evaluation.changed:
            changed.append(record_payload(evaluation.record))
    service.store.save(tuple(updated))
    return {
        "orders": [record_payload(item) for item in updated],
        "changed": changed,
        "active": sum(item.state is PendingOrderState.ACTIVE for item in updated),
        "triggered": sum(item.state is PendingOrderState.TRIGGERED for item in updated),
        "expired": sum(item.state is PendingOrderState.EXPIRED for item in updated),
    }

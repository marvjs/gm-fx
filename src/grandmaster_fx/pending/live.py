"""Real-account pending placement with broker confirmation and observability."""

from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from grandmaster_fx.config.demo_execution import DemoExecutionSettings
from grandmaster_fx.domain.symbols import SymbolSnapshot
from grandmaster_fx.execution.journal import ExecutionJournal
from grandmaster_fx.execution.risk import RiskManager
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway
from grandmaster_fx.pending.live_registry import (
    LivePendingRecord,
    LivePendingRegistry,
    LivePendingState,
)
from grandmaster_fx.pending.models import PendingOrderPlan

HISTORY_LOOKBACK_DAYS = 30
BROKER_VALUE_TOLERANCE = 1e-8


@dataclass(frozen=True, slots=True)
class LivePendingPlacement:
    """Inputs required to evaluate and submit one real-account pending order."""

    plan: PendingOrderPlan
    symbol: SymbolSnapshot
    balance: float
    settings: DemoExecutionSettings
    risk: RiskManager
    journal: ExecutionJournal
    registry_path: Path = Path("data/execution/live/pending_orders.json")


def _matches_active(record: LivePendingRecord, order: Any) -> bool:
    return bool(
        order.symbol == record.symbol
        and order.signal.value == record.direction
        and order.order_type == record.order_type
        and abs(order.price - record.trigger_price) <= BROKER_VALUE_TOLERANCE
        and abs(order.stop_loss - record.stop_loss) <= BROKER_VALUE_TOLERANCE
        and abs(order.take_profit - record.take_profit) <= BROKER_VALUE_TOLERANCE
        and abs(order.volume - record.volume) <= BROKER_VALUE_TOLERANCE
    )


def _history_state(order: dict[str, Any]) -> LivePendingState:
    state = str(order.get("state", "")).lower()
    reason = str(order.get("reason", "")).lower()
    text = f"{state} {reason}"
    if "expire" in text:
        return LivePendingState.EXPIRED
    if "cancel" in text:
        return LivePendingState.CANCELED
    if "reject" in text:
        return LivePendingState.REJECTED
    if "fill" in text:
        return LivePendingState.FILLED
    return LivePendingState.UNKNOWN


def _record_from_confirmation(
    request: LivePendingPlacement,
    ticket: int,
    volume: float,
    expiration: datetime,
    comment: str,
) -> LivePendingRecord:
    now = datetime.now(UTC).isoformat()
    return LivePendingRecord(
        identity=request.plan.identity,
        ticket=ticket,
        strategy_id=request.plan.strategy_id,
        symbol=request.plan.symbol,
        timeframe=request.plan.timeframe.value,
        direction=request.plan.signal.value,
        order_type=request.plan.order_type.value,
        source_time=request.plan.source_time.isoformat(),
        trigger_price=request.plan.trigger_price,
        stop_loss=request.plan.stop_loss,
        take_profit=request.plan.take_profit,
        volume=volume,
        expiration=expiration.isoformat(),
        magic=request.settings.execution.magic,
        comment=comment,
        placed_at=now,
        reconciled_at=now,
        state=LivePendingState.ACTIVE,
    )


def place_live_pending(  # noqa: PLR0911
    gateway: Mt5Gateway,
    request: LivePendingPlacement,
) -> dict[str, object]:
    """Submit an exact pending request and confirm the resulting broker state."""
    account = gateway.account()
    account.require_real()
    terminal = gateway.terminal()
    if not terminal.connected:
        return {"placed": False, "reason": "terminal_not_connected"}
    if not terminal.trade_allowed or terminal.trade_api_disabled:
        return {"placed": False, "reason": "terminal_trading_unavailable"}
    if not account.trade_allowed or not account.trade_expert:
        return {"placed": False, "reason": "account_trading_unavailable"}

    magic = request.settings.execution.magic
    existing = next(
        (
            item
            for item in gateway.pending_orders(magic)
            if item.symbol == request.plan.symbol
            and item.signal is request.plan.signal
            and request.plan.strategy_id in item.comment
        ),
        None,
    )
    if existing is not None:
        return {
            "placed": False,
            "reason": "existing_order_retained",
            "ticket": existing.ticket,
        }
    if any(item.symbol == request.plan.symbol for item in gateway.positions(magic)):
        return {"placed": False, "reason": "existing_position_conflict"}

    volume = request.risk.calculate_volume(
        request.balance,
        request.plan.trigger_price,
        request.plan.stop_loss,
        request.symbol,
    )
    expiration = datetime.now(UTC) + timedelta(
        minutes=request.plan.maximum_wait_bars * request.plan.timeframe.minutes
    )
    comment = f"{request.settings.execution.comment}:{request.plan.strategy_id}"[:31]
    request.journal.append(
        "live_pending_placement_started",
        identity=request.plan.identity,
        strategy_id=request.plan.strategy_id,
        symbol=request.plan.symbol,
        order_type=request.plan.order_type.value,
        volume=volume,
        magic=magic,
        dry_run=request.settings.execution.dry_run,
    )
    ticket = gateway.open_pending_order(
        request.plan,
        volume,
        magic,
        comment,
        request.settings.execution.deviation_points,
        expiration,
        request.settings.execution.dry_run,
    )
    if request.settings.execution.dry_run:
        request.journal.append(
            "live_pending_dry_run_completed",
            identity=request.plan.identity,
            symbol=request.plan.symbol,
            volume=volume,
            magic=magic,
        )
        return {
            "placed": False,
            "validated": True,
            "reason": "dry_run_pending_plan_validated",
            "ticket": None,
        }
    if ticket is None:
        request.journal.append(
            "live_pending_submission_uncertain",
            identity=request.plan.identity,
            symbol=request.plan.symbol,
            magic=magic,
            detail="gateway_returned_no_ticket",
        )
        return {"placed": False, "reason": "broker_confirmation_missing"}

    confirmation = next(
        (item for item in gateway.pending_orders(magic) if item.ticket == ticket),
        None,
    )
    if confirmation is None:
        request.journal.append(
            "live_pending_submission_uncertain",
            identity=request.plan.identity,
            ticket=ticket,
            symbol=request.plan.symbol,
            magic=magic,
            detail="ticket_not_found_in_active_orders",
        )
        return {
            "placed": False,
            "reason": "broker_confirmation_missing",
            "ticket": ticket,
        }

    record = _record_from_confirmation(request, ticket, volume, expiration, comment)
    if not _matches_active(record, confirmation):
        record = replace(
            record,
            state=LivePendingState.EXTERNALLY_MODIFIED,
            detail="broker_state_differs_from_submitted_plan",
        )
    LivePendingRegistry(request.registry_path).upsert(record)
    request.journal.append(
        "live_pending_placement_confirmed",
        identity=request.plan.identity,
        ticket=ticket,
        symbol=request.plan.symbol,
        state=record.state.value,
        magic=magic,
    )
    return {
        "placed": record.state is LivePendingState.ACTIVE,
        "reason": (
            "live_pending_order_confirmed"
            if record.state is LivePendingState.ACTIVE
            else "broker_state_mismatch"
        ),
        "ticket": ticket,
        "registry_state": record.state.value,
        "registry_path": str(request.registry_path),
    }


def list_live_pending(gateway: Mt5Gateway, magic: int) -> dict[str, object]:
    """List live-profile broker pending orders from a REAL account."""
    gateway.account().require_real()
    return {"orders": [asdict(item) for item in gateway.pending_orders(magic)]}


def reconcile_live_pending(
    gateway: Mt5Gateway,
    magic: int,
    registry_path: Path = Path("data/execution/live/pending_orders.json"),
) -> dict[str, object]:
    """Reconcile registry records against orders, positions, and broker history."""
    gateway.account().require_real()
    active = gateway.pending_orders(magic)
    positions = gateway.positions(magic)
    end = datetime.now(UTC)
    start = end - timedelta(days=HISTORY_LOOKBACK_DAYS)
    order_history = gateway.history_orders(start, end, magic)
    deal_history = gateway.history_deals(start, end, magic)
    registry = LivePendingRegistry(registry_path)
    updated: list[LivePendingRecord] = []
    for record in registry.load():
        order = next((item for item in active if item.ticket == record.ticket), None)
        if order is not None:
            state = (
                LivePendingState.ACTIVE
                if _matches_active(record, order)
                else LivePendingState.EXTERNALLY_MODIFIED
            )
            updated.append(replace(record, state=state, detail="active_order_observed"))
            continue
        if any(item.symbol == record.symbol for item in positions):
            updated.append(
                replace(
                    record,
                    state=LivePendingState.TRIGGERED,
                    detail="matching_open_position_observed",
                )
            )
            continue
        if any(int(item.get("order", -1)) == record.ticket for item in deal_history):
            updated.append(
                replace(record, state=LivePendingState.FILLED, detail="deal_history_match")
            )
            continue
        historical = next(
            (
                item
                for item in order_history
                if int(item.get("ticket", item.get("order", -1))) == record.ticket
            ),
            None,
        )
        if historical is not None:
            updated.append(
                replace(
                    record,
                    state=_history_state(historical),
                    detail="order_history_match",
                )
            )
            continue
        updated.append(replace(record, state=LivePendingState.MISSING, detail="no_broker_match"))
    reconciled = registry.reconcile(tuple(updated))
    return {
        "orders": [asdict(item) for item in active],
        "positions": [asdict(item) for item in positions],
        "registry": [asdict(item) for item in reconciled],
        "active": len(active),
        "triggered_positions": len(positions),
        "history_orders_checked": len(order_history),
        "history_deals_checked": len(deal_history),
        "registry_path": str(registry_path),
        "reconciled_at": end.isoformat(),
    }

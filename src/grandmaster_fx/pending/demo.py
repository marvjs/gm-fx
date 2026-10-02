"""Demo MT5 pending-order services."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta

from grandmaster_fx.config.demo_execution import DemoExecutionSettings
from grandmaster_fx.domain.symbols import SymbolSnapshot
from grandmaster_fx.execution.risk import RiskManager
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway
from grandmaster_fx.pending.models import PendingOrderPlan


@dataclass(frozen=True, slots=True)
class DemoPendingPlacement:
    plan: PendingOrderPlan
    symbol: SymbolSnapshot
    balance: float
    settings: DemoExecutionSettings
    risk: RiskManager


def place_demo_pending(gateway: Mt5Gateway, request: DemoPendingPlacement) -> dict[str, object]:
    gateway.account().require_demo()
    magic = request.settings.execution.magic
    existing = next(
        (
            x
            for x in gateway.pending_orders(magic)
            if x.symbol == request.plan.symbol and x.signal is request.plan.signal
        ),
        None,
    )
    if existing is not None:
        return {"placed": False, "reason": "existing_order_retained", "ticket": existing.ticket}
    volume = request.risk.calculate_volume(
        request.balance, request.plan.trigger_price, request.plan.stop_loss, request.symbol
    )
    expiry = datetime.now(UTC) + timedelta(
        minutes=request.plan.maximum_wait_bars * request.plan.timeframe.minutes
    )
    ticket = gateway.open_pending_order(
        request.plan,
        volume,
        magic,
        f"{request.settings.execution.comment}:{request.plan.strategy_id}"[:31],
        request.settings.execution.deviation_points,
        expiry,
        request.settings.execution.dry_run,
    )
    return {
        "placed": ticket is not None,
        "reason": "dry_run_pending_plan_validated"
        if request.settings.execution.dry_run
        else "demo_pending_order_placed",
        "ticket": ticket,
        "volume": volume,
        "expiration": expiry.isoformat(),
    }


def list_demo_pending(gateway: Mt5Gateway, magic: int) -> dict[str, object]:
    gateway.account().require_demo()
    return {"orders": [asdict(x) for x in gateway.pending_orders(magic)]}


def reconcile_demo_pending(gateway: Mt5Gateway, magic: int) -> dict[str, object]:
    gateway.account().require_demo()
    orders = gateway.pending_orders(magic)
    positions = gateway.positions(magic)
    return {
        "orders": [asdict(x) for x in orders],
        "positions": [asdict(x) for x in positions],
        "active": len(orders),
        "triggered_positions": len(positions),
        "reconciled_at": datetime.now(UTC).isoformat(),
    }

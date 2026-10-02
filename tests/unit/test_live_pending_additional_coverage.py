"""Additional branch coverage for live pending observability."""

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

from grandmaster_fx.config.demo_execution import (
    DemoExecutionSettings,
    load_demo_execution_settings,
)
from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.execution.journal import ExecutionJournal
from grandmaster_fx.execution.models import PendingOrderSnapshot
from grandmaster_fx.execution.risk import RiskManager
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway
from grandmaster_fx.pending.live import (
    LivePendingPlacement,
    list_live_pending,
    place_live_pending,
    reconcile_live_pending,
)
from grandmaster_fx.pending.live_registry import (
    LivePendingRecord,
    LivePendingRegistry,
    LivePendingState,
)
from grandmaster_fx.pending.models import PendingOrderPlan, PendingOrderType
from grandmaster_fx.strategies.models import Signal

if TYPE_CHECKING:
    from grandmaster_fx.domain.symbols import SymbolSnapshot

NOW = datetime(2026, 10, 1, tzinfo=UTC)


def plan() -> PendingOrderPlan:
    return PendingOrderPlan(
        identity="coverage-plan",
        strategy_id="momentum_continuation",
        symbol="USDJPYm",
        timeframe=Timeframe.M5,
        signal=Signal.BUY,
        order_type=PendingOrderType.BUY_STOP,
        source_time=NOW,
        trigger_price=101.0,
        stop_loss=99.0,
        take_profit=104.0,
        maximum_wait_bars=3,
        score=1.0,
    )


def settings(*, dry_run: bool) -> DemoExecutionSettings:
    loaded = load_demo_execution_settings()
    return loaded.model_copy(
        update={"execution": loaded.execution.model_copy(update={"dry_run": dry_run})}
    )


def gateway() -> Mock:
    value = Mock(spec=Mt5Gateway)
    value.account.return_value.require_real.return_value = None
    value.account.return_value.trade_allowed = True
    value.account.return_value.trade_expert = True
    value.terminal.return_value.connected = True
    value.terminal.return_value.trade_allowed = True
    value.terminal.return_value.trade_api_disabled = False
    value.pending_orders.return_value = []
    value.positions.return_value = []
    value.history_orders.return_value = []
    value.history_deals.return_value = []
    return value


def placement(tmp_path: Path, *, dry_run: bool) -> LivePendingPlacement:
    risk = Mock(spec=RiskManager)
    risk.calculate_volume.return_value = 0.1
    return LivePendingPlacement(
        plan=plan(),
        symbol=cast("SymbolSnapshot", Mock()),
        balance=10000.0,
        settings=settings(dry_run=dry_run),
        risk=risk,
        journal=ExecutionJournal(tmp_path / "journal.jsonl"),
        registry_path=tmp_path / "pending_orders.json",
    )


def broker_order(*, price: float = 101.0) -> PendingOrderSnapshot:
    return PendingOrderSnapshot(
        ticket=42,
        symbol="USDJPYm",
        signal=Signal.BUY,
        order_type=PendingOrderType.BUY_STOP.value,
        volume=0.1,
        price=price,
        stop_loss=99.0,
        take_profit=104.0,
        magic=settings(dry_run=False).execution.magic,
        comment="momentum_continuation",
        expiration=None,
    )


def registry_record(ticket: int) -> LivePendingRecord:
    return LivePendingRecord(
        identity=f"identity-{ticket}",
        ticket=ticket,
        strategy_id="momentum_continuation",
        symbol="USDJPYm",
        timeframe="M5",
        direction="BUY",
        order_type="buy_stop",
        source_time=NOW.isoformat(),
        trigger_price=101.0,
        stop_loss=99.0,
        take_profit=104.0,
        volume=0.1,
        expiration=NOW.isoformat(),
        magic=771101,
        comment="grandmaster-fx-live:momentum",
        placed_at=NOW.isoformat(),
        reconciled_at=NOW.isoformat(),
        state=LivePendingState.ACTIVE,
    )


def test_live_dry_run_reports_validation(tmp_path: Path) -> None:
    api = gateway()
    api.open_pending_order.return_value = None

    result = place_live_pending(api, placement(tmp_path, dry_run=True))

    assert result == {
        "placed": False,
        "validated": True,
        "reason": "dry_run_pending_plan_validated",
        "ticket": None,
    }


def test_live_submission_without_ticket_is_uncertain(tmp_path: Path) -> None:
    api = gateway()
    api.open_pending_order.return_value = None

    result = place_live_pending(api, placement(tmp_path, dry_run=False))

    assert result == {"placed": False, "reason": "broker_confirmation_missing"}


def test_live_submission_without_broker_confirmation(tmp_path: Path) -> None:
    api = gateway()
    api.open_pending_order.return_value = 42
    api.pending_orders.side_effect = [[], []]

    result = place_live_pending(api, placement(tmp_path, dry_run=False))

    assert result["placed"] is False
    assert result["reason"] == "broker_confirmation_missing"
    assert result["ticket"] == 42


def test_live_submission_detects_broker_mismatch(tmp_path: Path) -> None:
    api = gateway()
    api.open_pending_order.return_value = 42
    api.pending_orders.side_effect = [[], [broker_order(price=102.0)]]

    result = place_live_pending(api, placement(tmp_path, dry_run=False))

    assert result["placed"] is False
    assert result["reason"] == "broker_state_mismatch"
    assert result["registry_state"] == "externally_modified"


def test_live_list_serializes_pending_orders() -> None:
    api = gateway()
    api.pending_orders.return_value = [broker_order()]

    result = list_live_pending(api, 771101)

    orders = cast("list[dict[str, object]]", result["orders"])
    assert orders[0]["ticket"] == 42


def test_reconcile_classifies_expired_rejected_and_unknown(tmp_path: Path) -> None:
    path = tmp_path / "pending_orders.json"
    LivePendingRegistry(path).save((registry_record(1), registry_record(2), registry_record(3)))
    api = gateway()
    api.history_orders.return_value = [
        {"ticket": 1, "state": "expired", "reason": "time"},
        {"ticket": 2, "state": "rejected", "reason": "broker"},
        {"ticket": 3, "state": "removed", "reason": "other"},
    ]

    result = reconcile_live_pending(api, 771101, path)

    rows = cast("list[dict[str, object]]", result["registry"])
    states = {cast("int", row["ticket"]): cast("str", row["state"]) for row in rows}
    assert states == {1: "expired", 2: "rejected", 3: "unknown"}

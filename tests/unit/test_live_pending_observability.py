"""Live pending registry and read-only reconciliation tests."""

from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from unittest.mock import Mock

from grandmaster_fx.execution.models import PendingOrderSnapshot, PositionSnapshot
from grandmaster_fx.pending.live import reconcile_live_pending
from grandmaster_fx.pending.live_registry import (
    LivePendingRecord,
    LivePendingRegistry,
    LivePendingState,
)
from grandmaster_fx.strategies.models import Signal


def record(ticket: int = 42) -> LivePendingRecord:
    return LivePendingRecord(
        identity="identity",
        ticket=ticket,
        strategy_id="momentum_continuation",
        symbol="USDJPYm",
        timeframe="M5",
        direction="BUY",
        order_type="buy_stop",
        source_time="2026-10-01T10:00:00+00:00",
        trigger_price=101.0,
        stop_loss=99.0,
        take_profit=104.0,
        volume=0.1,
        expiration="2026-10-01T10:15:00+00:00",
        magic=771101,
        comment="grandmaster-fx-live:momentum",
        placed_at="2026-10-01T10:00:00+00:00",
        reconciled_at="2026-10-01T10:00:00+00:00",
        state=LivePendingState.ACTIVE,
    )


def gateway() -> Mock:
    value = Mock()
    value.pending_orders.return_value = []
    value.positions.return_value = []
    value.history_orders.return_value = []
    value.history_deals.return_value = []
    return value


def registry_rows(result: dict[str, object]) -> list[dict[str, object]]:
    """Narrow the reconciliation registry payload for strict static checkers."""
    return cast("list[dict[str, object]]", result["registry"])


def test_live_registry_round_trip(tmp_path: Path) -> None:
    registry = LivePendingRegistry(tmp_path / "pending_orders.json")
    registry.upsert(record())
    assert registry.load() == (record(),)


def test_reconcile_active_and_external_modification(tmp_path: Path) -> None:
    path = tmp_path / "pending_orders.json"
    LivePendingRegistry(path).upsert(record())
    broker = PendingOrderSnapshot(
        ticket=42,
        symbol="USDJPYm",
        signal=Signal.BUY,
        order_type="buy_stop",
        volume=0.1,
        price=101.0,
        stop_loss=99.0,
        take_profit=104.0,
        magic=771101,
        comment="grandmaster-fx-live:momentum",
        expiration=None,
    )
    api = gateway()
    api.pending_orders.return_value = [broker]
    result = reconcile_live_pending(api, 771101, path)
    assert registry_rows(result)[0]["state"] == "active"
    broker = replace(broker, price=102.0)
    api.pending_orders.return_value = [broker]
    changed = reconcile_live_pending(api, 771101, path)
    assert registry_rows(changed)[0]["state"] == "externally_modified"


def test_reconcile_history_and_missing_states(tmp_path: Path) -> None:
    path = tmp_path / "pending_orders.json"
    LivePendingRegistry(path).save((record(42), record(43), record(44)))
    api = gateway()
    api.history_deals.return_value = [{"order": 42}]
    api.history_orders.return_value = [{"ticket": 43, "state": "canceled", "reason": "client"}]
    result = reconcile_live_pending(api, 771101, path)
    states = {item["ticket"]: item["state"] for item in registry_rows(result)}
    assert states == {42: "filled", 43: "canceled", 44: "missing"}


def test_reconcile_matching_position_marks_triggered(tmp_path: Path) -> None:
    path = tmp_path / "pending_orders.json"
    LivePendingRegistry(path).upsert(record())
    api = gateway()
    api.positions.return_value = [
        PositionSnapshot(
            ticket=99,
            symbol="USDJPYm",
            signal=Signal.BUY,
            volume=0.1,
            price_open=101.0,
            price_current=102.0,
            stop_loss=99.0,
            take_profit=104.0,
            profit=10.0,
            magic=771101,
            opened_at=datetime(2026, 10, 1, tzinfo=UTC),
        )
    ]
    result = reconcile_live_pending(api, 771101, path)
    assert registry_rows(result)[0]["state"] == "triggered"

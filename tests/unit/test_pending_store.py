"""Persistent paper pending-order and duplicate tests."""

from datetime import UTC, datetime
from pathlib import Path

from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.pending.models import PendingOrderPlan, PendingOrderState, PendingOrderType
from grandmaster_fx.pending.service import PendingOrderService
from grandmaster_fx.pending.store import PendingOrderStore
from grandmaster_fx.strategies.models import Signal


def plan(identity: str = "plan-1") -> PendingOrderPlan:
    return PendingOrderPlan(
        identity=identity,
        strategy_id="momentum_continuation",
        symbol="USDJPYm",
        timeframe=Timeframe.M5,
        signal=Signal.BUY,
        order_type=PendingOrderType.BUY_STOP,
        source_time=datetime(2026, 1, 1, tzinfo=UTC),
        trigger_price=100.0,
        stop_loss=99.0,
        take_profit=102.0,
        maximum_wait_bars=3,
        score=0.8,
    )


def test_store_round_trip_and_restart(tmp_path: Path) -> None:
    path = tmp_path / "paper-pending.json"
    service = PendingOrderService(PendingOrderStore(path))
    placed, created = service.place(plan())
    assert created
    restarted = PendingOrderService(PendingOrderStore(path))
    restored = restarted.list()
    assert len(restored) == 1
    assert restored[0].plan == placed.plan
    assert restored[0].state is PendingOrderState.ACTIVE


def test_exact_duplicate_is_retained(tmp_path: Path) -> None:
    service = PendingOrderService(PendingOrderStore(tmp_path / "pending.json"))
    first, created = service.place(plan())
    duplicate, created_again = service.place(plan())
    assert created
    assert not created_again
    assert duplicate.plan.identity == first.plan.identity
    assert len(service.list()) == 1


def test_equivalent_candidate_duplicate_is_retained(tmp_path: Path) -> None:
    service = PendingOrderService(PendingOrderStore(tmp_path / "pending.json"))
    first, _created = service.place(plan("older"))
    duplicate, created = service.place(plan("newer"))
    assert not created
    assert duplicate.plan.identity == first.plan.identity


def test_store_returns_empty_when_missing(tmp_path: Path) -> None:
    store = PendingOrderStore(tmp_path / "no-file.json")
    assert store.load() == ()

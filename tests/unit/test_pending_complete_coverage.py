"""Coverage for the consolidated pending-order feature set."""

from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from grandmaster_fx.config import Mt5Secrets
from grandmaster_fx.config.demo_execution import load_demo_execution_settings
from grandmaster_fx.config.risk import load_risk_settings
from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.domain.mt5 import AccountTradeMode
from grandmaster_fx.execution.journal import ExecutionJournal
from grandmaster_fx.execution.models import PendingOrderSnapshot
from grandmaster_fx.execution.risk import RiskManager
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway
from grandmaster_fx.pending.demo import list_demo_pending, reconcile_demo_pending
from grandmaster_fx.pending.live import LivePendingPlacement, place_live_pending
from grandmaster_fx.pending.models import PendingOrderPlan, PendingOrderType
from grandmaster_fx.strategies.models import Signal


def plan() -> PendingOrderPlan:
    return PendingOrderPlan(
        identity="id",
        strategy_id="momentum_continuation",
        symbol="USDJPYm",
        timeframe=Timeframe.M5,
        signal=Signal.BUY,
        order_type=PendingOrderType.BUY_STOP,
        source_time=datetime(2026, 1, 1, tzinfo=UTC),
        trigger_price=101.0,
        stop_loss=99.0,
        take_profit=104.0,
        maximum_wait_bars=3,
        score=1.0,
    )


def module() -> Mock:
    value = Mock()
    value.TRADE_ACTION_PENDING = 5
    value.TRADE_ACTION_REMOVE = 8
    value.ORDER_TYPE_BUY_STOP = 4
    value.ORDER_TYPE_SELL_STOP = 5
    value.ORDER_TYPE_BUY_LIMIT = 2
    value.ORDER_TYPE_SELL_LIMIT = 3
    value.ORDER_TIME_SPECIFIED = 2
    value.ORDER_FILLING_RETURN = 2
    value.TRADE_RETCODE_DONE = 10009
    value.last_error.return_value = (0, "no error")
    value.orders_get.return_value = ()
    value.order_check.return_value = SimpleNamespace(retcode=0)
    value.order_send.return_value = SimpleNamespace(retcode=10009, order=42, comment="done")
    return value


def test_gateway_pending_order_dry_run_and_submission() -> None:
    mt5 = module()
    gateway = Mt5Gateway(Mt5Secrets(), mt5)
    expiration = datetime(2026, 1, 2, tzinfo=UTC)
    assert gateway.open_pending_order(plan(), 0.1, 771100, "demo", 10, expiration, True) is None
    assert gateway.open_pending_order(plan(), 0.1, 771100, "demo", 10, expiration, False) == 42


def test_gateway_pending_check_failure() -> None:
    mt5 = module()
    mt5.order_check.return_value = None
    gateway = Mt5Gateway(Mt5Secrets(), mt5)
    with pytest.raises(Exception, match="Pending order check failed"):
        gateway.open_pending_order(
            plan(), 0.1, 771100, "demo", 10, datetime(2026, 1, 2, tzinfo=UTC), False
        )


def test_gateway_cancel_unknown_and_owned() -> None:
    mt5 = module()
    gateway = Mt5Gateway(Mt5Secrets(), mt5)
    assert not gateway.cancel_pending_order(42, 771100, False)
    gateway.pending_orders = Mock(return_value=[SimpleNamespace(ticket=42)])
    assert gateway.cancel_pending_order(42, 771100, True)
    assert gateway.cancel_pending_order(42, 771100, False)


def test_demo_list_and_reconcile() -> None:
    gateway = Mock()
    gateway.pending_orders.return_value = []
    gateway.positions.return_value = []
    result = list_demo_pending(gateway, 771100)
    assert result == {"orders": []}
    reconciled = reconcile_demo_pending(gateway, 771100)
    assert reconciled["active"] == 0
    assert reconciled["triggered_positions"] == 0


def test_live_placement_success_and_failures(  # noqa: PLR0915
    tmp_path: Path,
) -> None:
    mt5 = module()
    gateway = Mt5Gateway(Mt5Secrets(), mt5)

    gateway.account = Mock()
    gateway.account.return_value.trade_mode = AccountTradeMode.REAL
    gateway.account.return_value.trade_allowed = True
    gateway.account.return_value.trade_expert = True

    gateway.terminal = Mock()
    gateway.terminal.return_value.connected = True
    gateway.terminal.return_value.trade_allowed = True
    gateway.terminal.return_value.trade_api_disabled = False

    gateway.pending_orders = Mock(return_value=[])
    gateway.positions = Mock(return_value=[])

    symbol_mock = Mock()
    symbol_mock.tick_size = 0.00001
    symbol_mock.tick_value = 1.0
    symbol_mock.normalize_volume = lambda _value: 0.1

    settings = load_demo_execution_settings()
    settings = settings.model_copy(
        update={"execution": settings.execution.model_copy(update={"dry_run": False})}
    )

    request = LivePendingPlacement(
        plan=plan(),
        symbol=symbol_mock,
        balance=1000.0,
        settings=settings,
        risk=RiskManager(load_risk_settings()),
        journal=ExecutionJournal(tmp_path / "journal.jsonl"),
    )

    # 1. Terminal not connected
    gateway.terminal.return_value.connected = False
    res1 = place_live_pending(gateway, request)
    assert res1["placed"] is False
    assert res1["reason"] == "terminal_not_connected"
    gateway.terminal.return_value.connected = True

    # 2. Terminal trading disabled
    gateway.terminal.return_value.trade_allowed = False
    res2 = place_live_pending(gateway, request)
    assert res2["placed"] is False
    assert res2["reason"] == "terminal_trading_unavailable"
    gateway.terminal.return_value.trade_allowed = True

    # 3. Account trading disabled
    gateway.account.return_value.trade_allowed = False
    res3 = place_live_pending(gateway, request)
    assert res3["placed"] is False
    assert res3["reason"] == "account_trading_unavailable"
    gateway.account.return_value.trade_allowed = True

    # 4. Existing pending order retained
    gateway.pending_orders.return_value = [
        Mock(symbol="USDJPYm", signal=Signal.BUY, comment="momentum_continuation", ticket=999)
    ]
    res4 = place_live_pending(gateway, request)
    assert res4["placed"] is False
    assert res4["reason"] == "existing_order_retained"
    gateway.pending_orders.return_value = []

    # 5. Conflicting open position
    gateway.positions.return_value = [Mock(symbol="USDJPYm")]
    res5 = place_live_pending(gateway, request)
    assert res5["placed"] is False
    assert res5["reason"] == "existing_position_conflict"
    gateway.positions.return_value = []

    # 6. Successful placement requires post-submission broker confirmation.
    confirmed = PendingOrderSnapshot(
        ticket=42,
        symbol="USDJPYm",
        signal=Signal.BUY,
        order_type=PendingOrderType.BUY_STOP.value,
        volume=0.1,
        price=101.0,
        stop_loss=99.0,
        take_profit=104.0,
        magic=settings.execution.magic,
        comment=f"{settings.execution.comment}:momentum_continuation"[:31],
        expiration=None,
    )
    gateway.pending_orders.side_effect = [[], [confirmed]]
    request = LivePendingPlacement(
        plan=request.plan,
        symbol=request.symbol,
        balance=request.balance,
        settings=request.settings,
        risk=request.risk,
        journal=request.journal,
        registry_path=tmp_path / "pending_orders.json",
    )

    res6 = place_live_pending(gateway, request)

    assert res6["placed"] is True
    assert res6["reason"] == "live_pending_order_confirmed"
    assert res6["ticket"] == 42
    assert res6["registry_state"] == "active"
    assert (tmp_path / "pending_orders.json").is_file()

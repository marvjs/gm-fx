"""Execution manager tests."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

from grandmaster_fx.config.demo_execution import load_demo_execution_settings
from grandmaster_fx.config.risk import load_risk_settings
from grandmaster_fx.domain.mt5 import AccountSnapshot
from grandmaster_fx.domain.symbols import ForexIdentity, SymbolSnapshot
from grandmaster_fx.execution.manager import ExecutionManager
from grandmaster_fx.execution.models import (
    CloseReason,
    ExecutionCandidate,
    PositionSnapshot,
    ProfitTrail,
)
from grandmaster_fx.execution.risk import RiskManager
from grandmaster_fx.strategies.models import Signal


def account(*, balance: float = 1000, equity: float = 1000) -> AccountSnapshot:
    return AccountSnapshot.from_mapping(
        {
            "login": 1,
            "trade_mode": 0,
            "server": "Demo",
            "company": "Broker",
            "currency": "USD",
            "leverage": 100,
            "balance": balance,
            "equity": equity,
            "margin": 0,
            "margin_free": equity,
            "profit": equity - balance,
            "trade_allowed": True,
            "trade_expert": True,
        }
    )


def symbol_snapshot() -> SymbolSnapshot:
    return SymbolSnapshot(
        name="EURUSDm",
        identity=ForexIdentity("EURUSD", "EUR", "USD"),
        description="",
        selected=True,
        visible=True,
        trade_mode=4,
        digits=5,
        point=0.00001,
        spread_points=5,
        spread_float=True,
        tick_size=0.00001,
        tick_value=1.0,
        contract_size=100000.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        volume_limit=0.0,
        stops_level=0,
        freeze_level=0,
    )


def position(profit: float = 0.0) -> PositionSnapshot:
    return PositionSnapshot(
        10, "EURUSDm", Signal.BUY, 0.01, 1.0, 1.0, 0.99, 1.01, profit, 771100, datetime.now(UTC)
    )


def test_profit_trail_small_profit_and_retracement() -> None:
    trail = ProfitTrail()
    assert trail.update(0.8, 0.75, 0.25, 1.0) is None
    assert trail.update(0.5, 0.75, 0.25, 1.0) is CloseReason.PROFIT_RETRACEMENT
    assert ProfitTrail().update(1.0, 0.75, 0.25, 1.0) is CloseReason.SMALL_PROFIT


def test_manager_closes_retracing_position() -> None:
    gateway = Mock()
    gateway.account.return_value = account()

    # 0.40 hits the 0.30 trailing activation, but is below the 0.50 instant-close target
    gateway.positions.return_value = [position(0.4)]
    gateway.close_position.return_value = True

    manager = ExecutionManager(
        gateway=gateway,
        settings=load_demo_execution_settings(),
        risk_manager=RiskManager(load_risk_settings()),
        allowed_currencies=frozenset(),
        allow_live_account=False,
    )
    assert manager.monitor() == ()

    # 0.20 is a drop of 0.20 from the peak of 0.40, triggering the 0.15 retracement exit
    gateway.positions.return_value = [position(0.2)]
    assert manager.monitor() == (10,)


def test_manager_ranks_and_opens_unique_symbols(tmp_path: Path) -> None:
    settings_path = tmp_path / "execution.toml"
    settings_path.write_text(
        Path("configs/demo_execution.toml")
        .read_text()
        .replace("enabled = false", "enabled = true"),
        encoding="utf-8",
    )
    gateway = Mock()
    gateway.account.return_value = account()
    gateway.positions.return_value = []
    gateway.symbol.return_value = symbol_snapshot()
    gateway.open_order.return_value = 1

    manager = ExecutionManager(
        gateway=gateway,
        settings=load_demo_execution_settings(settings_path),
        risk_manager=RiskManager(load_risk_settings()),
        allowed_currencies=frozenset({"EUR", "USD", "GBP"}),
        allow_live_account=False,
    )
    candidates = [
        ExecutionCandidate("EURUSDm", Signal.BUY, 0.8, 1.10, 1.09, 1.12),
        ExecutionCandidate("GBPUSDm", Signal.SELL, 0.9, 1.30, 1.31, 1.28),
    ]
    assert manager.execute(candidates) == ("GBPUSDm", "EURUSDm")

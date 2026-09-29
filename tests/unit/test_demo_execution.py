"""Demo execution manager tests."""

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

from grandmaster_fx.config.demo_execution import load_demo_execution_settings
from grandmaster_fx.domain.mt5 import AccountSnapshot
from grandmaster_fx.execution.manager import DemoExecutionManager
from grandmaster_fx.execution.models import (
    CloseReason,
    ExecutionCandidate,
    PositionSnapshot,
    ProfitTrail,
)
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
    gateway.positions.return_value = [position(0.8)]
    gateway.close_demo_position.return_value = True
    manager = DemoExecutionManager(gateway, load_demo_execution_settings(), Mock())
    assert manager.monitor() == ()
    gateway.positions.return_value = [position(0.5)]
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
    gateway.open_demo_order.return_value = None
    manager = DemoExecutionManager(gateway, load_demo_execution_settings(settings_path), Mock())
    candidates = [
        ExecutionCandidate("EURUSDm", Signal.BUY, 0.8, 0.99, 1.01),
        ExecutionCandidate("GBPUSDm", Signal.SELL, 0.9, 1.01, 0.99),
    ]
    assert manager.execute(candidates) == ("GBPUSDm", "EURUSDm")

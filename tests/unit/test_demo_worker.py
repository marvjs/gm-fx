"""Execution worker lifecycle and strategy orchestration tests."""

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import Mock

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.domain.symbols import ForexIdentity, SymbolSnapshot
from grandmaster_fx.exceptions import Mt5DataError
from grandmaster_fx.execution.models import PositionSnapshot
from grandmaster_fx.execution.worker import ExecutionWorker
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


def _mocked_worker_dependencies(tmp_path: Path) -> tuple[Mock, Mock, Mock]:
    gateway = Mock()
    manager = Mock()
    manager.settings.execution.magic = 123
    manager.settings.execution.poll_interval_seconds = 0.01

    account = Mock()
    account.balance = 1000.0
    account.equity = 1000.0
    account.margin = 0.0
    gateway.account.return_value = account
    gateway.positions.return_value = []
    gateway.pending_orders.return_value = []

    gateway.symbols.return_value = [
        SymbolSnapshot(
            name="EURUSDm",
            identity=ForexIdentity("EURUSD", "EUR", "USD"),
            description="Euro",
            selected=True,
            visible=True,
            trade_mode=4,
            digits=5,
            point=0.00001,
            spread_points=8,
            spread_float=True,
            tick_size=0.00001,
            tick_value=1.0,
            contract_size=100000.0,
            volume_min=0.01,
            volume_max=200.0,
            volume_step=0.01,
            volume_limit=0.0,
            stops_level=0,
            freeze_level=0,
        )
    ]
    gateway.symbol.return_value = gateway.symbols.return_value[0]

    base = datetime(2026, 1, 1, tzinfo=UTC)
    gateway.bars.return_value = [
        Bar(base + timedelta(minutes=i), 1, 1, 1, 1, 1, 1, 0) for i in range(15)
    ]

    strategy = Mock()
    strategy.minimum_bars = 10
    strategy.evaluate.return_value = StrategyDecision(
        signal=Signal.BUY,
        symbol="EURUSDm",
        timestamp=datetime.now(UTC),
        entry=1.0,
        stop_loss=0.9,
        take_profit=1.1,
        reward_risk=2.0,
        reasons=(DecisionReason.BUY_SETUP_CONFIRMED,),
    )

    return gateway, manager, strategy


def test_demo_worker_status_and_cycle(tmp_path: Path) -> None:
    gateway, manager, strategy = _mocked_worker_dependencies(tmp_path)

    manager.monitor.return_value = (1,)
    manager.execute.return_value = ("EURUSDm",)

    pos = PositionSnapshot(
        ticket=1,
        symbol="EURUSDm",
        signal=Signal.BUY,
        volume=0.01,
        price_open=1.0,
        price_current=1.1,
        stop_loss=0.9,
        take_profit=1.2,
        profit=10.0,
        magic=123,
        opened_at=datetime.now(UTC),
    )
    gateway.positions.return_value = [pos]

    worker = ExecutionWorker(
        gateway=gateway,
        manager=manager,
        strategy=strategy,
        timeframe=Timeframe.M5,
        symbols=("EURUSD",),
        allowed_currencies=frozenset({"EUR", "USD"}),
        stop_path=tmp_path / "STOP",
    )

    cycle_res = worker.cycle()
    assert cycle_res["closed"] == (1,)
    assert cycle_res["opened"] == ("EURUSDm",)
    assert cycle_res["balance"] == 1000.0

    positions = cycle_res["positions"]
    assert isinstance(positions, list)
    assert len(positions) == 1


def test_demo_worker_run_honors_maximum_cycles(tmp_path: Path) -> None:
    gateway, manager, strategy = _mocked_worker_dependencies(tmp_path)
    worker = ExecutionWorker(
        gateway=gateway,
        manager=manager,
        strategy=strategy,
        timeframe=Timeframe.M5,
        symbols=(),
        allowed_currencies=frozenset({"EUR", "USD"}),
        stop_path=tmp_path / "STOP",
    )
    worker.cycle = Mock(return_value={"closed": [], "opened": []})  # type: ignore[method-assign]
    worker.run(maximum_cycles=2)
    assert worker.cycle.call_count == 2
    assert not worker.stop_path.exists()


def test_demo_worker_request_stop(tmp_path: Path) -> None:
    worker = ExecutionWorker(
        gateway=Mock(),
        manager=Mock(),
        strategy=Mock(),
        timeframe=Timeframe.M5,
        symbols=(),
        allowed_currencies=frozenset(),
        stop_path=tmp_path / "STOP",
    )
    worker.request_stop()
    assert worker.stop_path.is_file()


def test_demo_worker_cycle_ignores_evaluation_exceptions(tmp_path: Path) -> None:
    gateway, manager, strategy = _mocked_worker_dependencies(tmp_path)

    manager.monitor.return_value = ()
    manager.execute.return_value = ()

    gateway.symbols.side_effect = Mt5DataError("Simulated MT5 exception")

    worker = ExecutionWorker(
        gateway=gateway,
        manager=manager,
        strategy=strategy,
        timeframe=Timeframe.M5,
        symbols=("EURUSD",),
        allowed_currencies=frozenset({"EUR", "USD"}),
    )

    res = worker.cycle()
    assert res["opened"] == ()
    assert res["balance"] == 1000.0

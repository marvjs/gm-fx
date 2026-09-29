"""Research analysis tests."""

from datetime import UTC, datetime

from grandmaster_fx.backtesting.metrics import calculate_metrics
from grandmaster_fx.backtesting.models import BacktestResult, ExitReason, SimulatedTrade
from grandmaster_fx.research.analysis import analyze_result
from grandmaster_fx.strategies.models import Signal


def trade(signal: Signal, pnl: float, hour: int, reason: ExitReason) -> SimulatedTrade:
    timestamp = datetime(2026, 1, 5, hour, tzinfo=UTC)
    return SimulatedTrade(
        "EURUSDm",
        signal,
        timestamp,
        timestamp,
        1,
        1,
        0.9,
        1.1,
        0.1,
        pnl + 1,
        1,
        pnl,
        pnl / 10,
        1,
        reason,
    )


def test_analysis_groups_trades_and_costs() -> None:
    trades = [
        trade(Signal.BUY, 10, 8, ExitReason.TAKE_PROFIT),
        trade(Signal.SELL, -5, 9, ExitReason.STOP_LOSS),
    ]
    equity, metrics = calculate_metrics(1000, trades)
    result = BacktestResult("EURUSDm", tuple(trades), equity, metrics)
    analysis = analyze_result(result)
    assert len(analysis.by_signal) == 2
    assert len(analysis.by_exit_reason) == 2
    assert len(analysis.by_hour) == 2
    assert analysis.costs.total_costs == 2
    assert analysis.costs.net_profit == 5

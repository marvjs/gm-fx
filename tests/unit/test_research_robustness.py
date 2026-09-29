"""Robustness research tests."""

from datetime import UTC, datetime

from grandmaster_fx.backtesting.models import (
    BacktestMetrics,
    BacktestResult,
    ExitReason,
    SimulatedTrade,
)
from grandmaster_fx.research.robustness import ablations, portfolio_summary
from grandmaster_fx.strategies.models import Signal


def result(symbol: str, net: float, factor: float, drawdown: float) -> BacktestResult:
    metrics = BacktestMetrics(
        1000,
        1000 + net,
        net,
        net / 10,
        drawdown,
        10,
        5,
        5,
        50,
        factor,
        net / 10,
        10,
        10,
        1,
        3,
    )
    return BacktestResult(symbol, (), (1000, 1000 + net), metrics)


def trade(signal: Signal, holding: int, pnl: float) -> SimulatedTrade:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return SimulatedTrade(
        "EURUSDm",
        signal,
        now,
        now,
        1,
        1,
        0.9,
        1.1,
        0.1,
        pnl,
        0,
        pnl,
        pnl / 10,
        holding,
        ExitReason.TIME_STOP,
    )


def test_portfolio_summary_marks_consistent_folds_stable() -> None:
    summary = portfolio_summary((result("A", 10, 1.2, 5), result("B", 20, 1.1, 6)))
    assert summary.stable
    assert summary.profitable_folds == 2
    assert summary.aggregate_net_profit == 30


def test_portfolio_summary_marks_losing_mix_unstable() -> None:
    summary = portfolio_summary((result("A", 10, 1.2, 5), result("B", -20, 0.8, 16)))
    assert not summary.stable
    assert summary.worst_drawdown_percent == 16


def test_ablations_split_direction_and_holding_period() -> None:
    trades = (
        trade(Signal.BUY, 2, 10),
        trade(Signal.SELL, 8, -5),
    )
    base = result("EURUSDm", 5, 1.1, 5)
    report = ablations(BacktestResult(base.symbol, trades, base.equity_curve, base.metrics))
    indexed = {item.label: item for item in report}
    assert indexed["BUY"].net_profit == 10
    assert indexed["SELL"].net_profit == -5
    assert indexed["holding<=5"].trades == 1
    assert indexed["holding>5"].trades == 1

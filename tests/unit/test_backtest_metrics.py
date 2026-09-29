"""Backtest metric tests."""

from datetime import UTC, datetime

from grandmaster_fx.backtesting.metrics import calculate_metrics
from grandmaster_fx.backtesting.models import ExitReason, SimulatedTrade
from grandmaster_fx.strategies.models import Signal


def trade(pnl: float) -> SimulatedTrade:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    return SimulatedTrade(
        "EURUSD",
        Signal.BUY,
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
        1,
        ExitReason.TAKE_PROFIT if pnl > 0 else ExitReason.STOP_LOSS,
    )


def test_metrics_known_values() -> None:
    equity, m = calculate_metrics(1000, [trade(100), trade(-50), trade(-25)])
    assert equity == (1000, 1100, 1050, 1025)
    assert m.net_profit == 25
    assert m.trade_count == 3
    assert m.maximum_consecutive_losses == 2
    assert m.profit_factor == 100 / 75


def test_empty_metrics() -> None:
    _, m = calculate_metrics(1000, [])
    assert m.trade_count == 0
    assert m.final_balance == 1000

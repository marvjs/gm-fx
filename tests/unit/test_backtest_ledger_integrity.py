"""Backtest trade-ledger timestamp integrity tests."""

from datetime import UTC, datetime, timedelta

import pytest

from grandmaster_fx.backtesting.engine import CloseContext, OpenTrade, _close
from grandmaster_fx.backtesting.models import ExitReason, SimulatedTrade
from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.models import Signal


def bar(minutes: int) -> Bar:
    """Return one deterministic candle."""
    return Bar(
        time=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minutes),
        open=1.0,
        high=1.1,
        low=0.9,
        close=1.05,
        tick_volume=10,
        spread=5,
        real_volume=0,
    )


def open_trade(entry_minute: int = 5) -> OpenTrade:
    """Return one open buy position with its real entry timestamp."""
    return OpenTrade(
        signal=Signal.BUY,
        entry_index=entry_minute,
        entry_time=bar(entry_minute).time,
        entry=1.0,
        stop=0.9,
        target=1.1,
        volume=0.1,
        risk_cash=25.0,
    )


def test_multi_bar_close_preserves_original_entry_time() -> None:
    trade = open_trade(5)
    exit_bar = bar(9)
    context = CloseContext(
        symbol="EURUSDm",
        bar=exit_bar,
        index=9,
        price=1.1,
        reason=ExitReason.TAKE_PROFIT,
        contract_size=100_000,
        commission=7.0,
    )
    closed = _close(trade, context)
    assert closed.entry_time == bar(5).time
    assert closed.exit_time == exit_bar.time
    assert closed.holding_bars == 4
    assert closed.exit_time > closed.entry_time


def test_same_bar_exit_has_equal_valid_timestamps() -> None:
    trade = open_trade(5)
    exit_bar = bar(5)
    context = CloseContext(
        symbol="EURUSDm",
        bar=exit_bar,
        index=5,
        price=0.9,
        reason=ExitReason.STOP_LOSS,
        contract_size=100_000,
        commission=7.0,
    )
    closed = _close(trade, context)
    assert closed.entry_time == closed.exit_time
    assert closed.holding_bars == 0


def test_trade_rejects_exit_before_entry() -> None:
    entry = datetime(2026, 1, 1, 0, 5, tzinfo=UTC)
    with pytest.raises(ValueError, match="cannot precede"):
        SimulatedTrade(
            symbol="EURUSDm",
            signal=Signal.BUY,
            entry_time=entry,
            exit_time=entry - timedelta(minutes=1),
            entry=1.0,
            exit=0.9,
            stop_loss=0.9,
            take_profit=1.1,
            volume=0.1,
            gross_pnl=-100.0,
            costs=0.7,
            net_pnl=-100.7,
            return_r=-1.0,
            holding_bars=0,
            exit_reason=ExitReason.STOP_LOSS,
        )


def test_trade_rejects_negative_holding_bars() -> None:
    timestamp = datetime(2026, 1, 1, tzinfo=UTC)
    with pytest.raises(ValueError, match="cannot be negative"):
        SimulatedTrade(
            symbol="EURUSDm",
            signal=Signal.BUY,
            entry_time=timestamp,
            exit_time=timestamp,
            entry=1.0,
            exit=1.0,
            stop_loss=0.9,
            take_profit=1.1,
            volume=0.1,
            gross_pnl=0.0,
            costs=0.7,
            net_pnl=-0.7,
            return_r=-0.01,
            holding_bars=-1,
            exit_reason=ExitReason.TIME_STOP,
        )

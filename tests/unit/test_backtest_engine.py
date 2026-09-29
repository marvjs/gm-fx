"""Backtesting engine unit and orchestration tests."""

from datetime import UTC, datetime, timedelta

import pytest

from grandmaster_fx.backtesting import engine
from grandmaster_fx.backtesting.engine import (
    BacktestInput,
    CloseContext,
    OpenTrade,
    _close,
    _exit_price,
    _volume,
    run_backtest,
)
from grandmaster_fx.backtesting.models import ExitReason
from grandmaster_fx.config.backtest import (
    BacktestParameters,
    BacktestSettings,
    DataQualityParameters,
)
from grandmaster_fx.config.strategy import (
    ProtectionParameters,
    StrategyFilters,
    StrategyParameters,
    StrategySettings,
)
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.strategies.adapters import BaselineStrategyAdapter
from grandmaster_fx.strategies.models import (
    DecisionReason,
    Signal,
    StrategyDecision,
)


def bar(index: int, *, high: float = 1.01, low: float = 0.99, close: float = 1.0) -> Bar:
    return Bar(
        time=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=index),
        open=1.0,
        high=high,
        low=low,
        close=close,
        tick_volume=10,
        spread=5,
        real_volume=0,
    )


def strategy_settings() -> StrategySettings:
    return StrategySettings(
        strategy=StrategyParameters(
            name="test",
            enabled=True,
            fast_ema_period=3,
            slow_ema_period=5,
            rsi_period=3,
            atr_period=3,
            roc_period=2,
            minimum_bars=6,
        ),
        filters=StrategyFilters(
            max_spread_points=15,
            minimum_atr_points=1,
            maximum_atr_points=10_000,
            minimum_roc_percent=0,
            buy_rsi_min=0,
            buy_rsi_max=100,
            sell_rsi_min=0,
            sell_rsi_max=100,
            session_start_utc=0,
            session_end_utc=24,
        ),
        protection=ProtectionParameters(
            stop_atr_multiple=1,
            target_atr_multiple=2,
            minimum_reward_risk=1,
        ),
    )


def backtest_settings(*, maximum_holding: int = 3) -> BacktestSettings:
    return BacktestSettings(
        backtest=BacktestParameters(
            initial_balance=10_000,
            risk_per_trade_percent=0.25,
            commission_per_lot_round_turn=7,
            slippage_points=2,
            maximum_holding_bars=maximum_holding,
            minimum_history_bars=6,
            conservative_same_bar_exit=True,
        ),
        quality=DataQualityParameters(maximum_gap_multiple=3, maximum_data_age_hours=24),
    )


def open_trade(signal: Signal = Signal.BUY) -> OpenTrade:
    return OpenTrade(
        signal,
        5,
        datetime(2026, 1, 1, 0, 5, tzinfo=UTC),
        1.0,
        0.9 if signal is Signal.BUY else 1.1,
        1.1 if signal is Signal.BUY else 0.9,
        0.1,
        25,
    )


def test_volume_calculation_and_invalid_stop() -> None:
    volume, risk = _volume(10_000, 0.25, 1.0, 0.99, 100_000)
    assert volume == 0.02
    assert risk == 25
    with pytest.raises(ValueError, match="stop distance"):
        _volume(10_000, 0.25, 1.0, 1.0, 100_000)


@pytest.mark.parametrize(
    ("trade", "current", "reason"),
    [
        (open_trade(Signal.BUY), bar(6, low=0.89), ExitReason.STOP_LOSS),
        (open_trade(Signal.BUY), bar(6, high=1.11), ExitReason.TAKE_PROFIT),
        (open_trade(Signal.SELL), bar(6, high=1.11), ExitReason.STOP_LOSS),
        (open_trade(Signal.SELL), bar(6, low=0.89), ExitReason.TAKE_PROFIT),
    ],
)
def test_protective_exits(trade: OpenTrade, current: Bar, reason: ExitReason) -> None:
    outcome = _exit_price(trade, current, 2, 0.00001, 20, 6)
    assert outcome is not None
    assert outcome[1] is reason


def test_time_stop_and_no_exit() -> None:
    trade = open_trade()
    assert _exit_price(trade, bar(6), 0, 0.00001, 20, 6) is None
    outcome = _exit_price(trade, bar(8), 0, 0.00001, 3, 8)
    assert outcome == (1.0, ExitReason.TIME_STOP)


def test_close_calculates_costs_and_holding_period() -> None:
    current = bar(7, close=1.1)
    context = CloseContext("EURUSDm", current, 7, 1.1, ExitReason.TAKE_PROFIT, 100_000, 7)
    trade = _close(open_trade(), context)
    assert trade.gross_pnl == pytest.approx(1_000)
    assert trade.costs == pytest.approx(0.7)
    assert trade.holding_bars == 2
    assert trade.net_pnl == pytest.approx(999.3)


def decision(signal: Signal, timestamp: datetime) -> StrategyDecision:
    actionable = signal is not Signal.HOLD
    return StrategyDecision(
        signal=signal,
        symbol="EURUSDm",
        timestamp=timestamp,
        entry=1.0 if actionable else None,
        stop_loss=0.99 if actionable else None,
        take_profit=1.01 if actionable else None,
        reward_risk=1.0 if actionable else None,
        reasons=(
            DecisionReason.BUY_SETUP_CONFIRMED if actionable else DecisionReason.TREND_NOT_ALIGNED,
        ),
    )


def test_run_backtest_without_signals(monkeypatch: pytest.MonkeyPatch) -> None:
    data = [bar(index) for index in range(10)]
    monkeypatch.setattr(
        engine,
        "_evaluate_strategy",
        lambda *_args: decision(Signal.HOLD, data[-1].time),
    )
    request = BacktestInput(
        "EURUSDm",
        data,
        Timeframe.M1,
        0.00001,
        100_000,
        BaselineStrategyAdapter(strategy_settings()),
    )
    result = run_backtest(request, backtest_settings())
    assert result.metrics.trade_count == 0
    assert result.metrics.final_balance == 10_000


def test_run_backtest_opens_and_closes_trade(monkeypatch: pytest.MonkeyPatch) -> None:
    data = [bar(index, high=1.02, low=0.98) for index in range(10)]
    calls = 0

    def fake_decision(*_args: object) -> StrategyDecision:
        nonlocal calls
        calls += 1
        return decision(Signal.BUY if calls == 1 else Signal.HOLD, data[-1].time)

    monkeypatch.setattr(engine, "_evaluate_strategy", fake_decision)
    request = BacktestInput(
        "EURUSDm",
        data,
        Timeframe.M1,
        0.00001,
        100_000,
        BaselineStrategyAdapter(strategy_settings()),
    )
    result = run_backtest(request, backtest_settings())
    assert result.metrics.trade_count == 1
    assert result.trades[0].exit_reason is ExitReason.STOP_LOSS


def test_run_backtest_closes_open_trade_at_end(monkeypatch: pytest.MonkeyPatch) -> None:
    data = [bar(index, high=1.005, low=0.995) for index in range(8)]
    monkeypatch.setattr(
        engine,
        "_evaluate_strategy",
        lambda *_args: decision(Signal.BUY, data[-1].time),
    )
    request = BacktestInput(
        "EURUSDm",
        data,
        Timeframe.M1,
        0.00001,
        100_000,
        BaselineStrategyAdapter(strategy_settings()),
    )
    result = run_backtest(request, backtest_settings(maximum_holding=20))
    assert result.trades[-1].exit_reason is ExitReason.END_OF_DATA

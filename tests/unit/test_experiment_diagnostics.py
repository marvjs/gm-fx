"""Experiment diagnostics tests."""

from datetime import UTC, datetime, timedelta

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.experiments.diagnostics import collect_diagnostics
from grandmaster_fx.strategies.models import DecisionReason, Signal, StrategyDecision


class Strategy:
    identifier = "test"
    minimum_bars = 2

    def evaluate(self, symbol: str, bars: list[Bar], _point: float) -> StrategyDecision:
        signal = Signal.BUY if len(bars) % 2 == 0 else Signal.HOLD
        return StrategyDecision(
            signal,
            symbol,
            bars[-1].time,
            1 if signal is Signal.BUY else None,
            0.9 if signal is Signal.BUY else None,
            1.1 if signal is Signal.BUY else None,
            1 if signal is Signal.BUY else None,
            (
                DecisionReason.BUY_SETUP_CONFIRMED
                if signal is Signal.BUY
                else DecisionReason.TREND_NOT_ALIGNED,
            ),
        )


def test_collect_diagnostics_counts_activity() -> None:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    bars = [Bar(start + timedelta(minutes=i), 1, 1.1, 0.9, 1, 1, 1, 0) for i in range(6)]
    result = collect_diagnostics(Strategy(), "EURUSDm", bars, 0.00001)
    assert result.bars_evaluated == 4
    assert result.actionable_signals == 2
    assert result.buy_signals == 2
    assert result.signal_frequency_percent == 50

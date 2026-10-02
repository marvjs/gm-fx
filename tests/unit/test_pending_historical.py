"""Focused branch coverage for chronological pending-entry backtesting."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import TYPE_CHECKING, cast
from unittest.mock import Mock

import pytest

from grandmaster_fx.backtesting.engine import BacktestInput
from grandmaster_fx.config.backtest import BacktestSettings
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.pending import historical
from grandmaster_fx.pending.models import (
    PendingEvaluation,
    PendingOrderPlan,
    PendingOrderRecord,
    PendingOrderState,
    PendingOrderType,
)
from grandmaster_fx.strategies.models import Signal

if TYPE_CHECKING:
    from grandmaster_fx.strategies.protocol import ResearchStrategy


NOW = datetime(2026, 1, 1, tzinfo=UTC)


def bars(count: int = 8) -> list[Bar]:
    return [
        Bar(
            NOW + timedelta(minutes=5 * index),
            100.0,
            102.0,
            98.0,
            100.0,
            1,
            1,
            0,
        )
        for index in range(count)
    ]


def pending_plan() -> PendingOrderPlan:
    return PendingOrderPlan(
        identity="pending-plan",
        strategy_id="momentum_continuation",
        symbol="USDJPYm",
        timeframe=Timeframe.M5,
        signal=Signal.BUY,
        order_type=PendingOrderType.BUY_STOP,
        source_time=NOW,
        trigger_price=101.0,
        stop_loss=99.0,
        take_profit=104.0,
        maximum_wait_bars=3,
        score=1.0,
    )


def request() -> BacktestInput:
    strategy = Mock(identifier="momentum_continuation", minimum_bars=2)
    strategy.evaluate.return_value = Mock()
    return BacktestInput(
        symbol="USDJPYm",
        bars=bars(),
        timeframe=Timeframe.M5,
        point=0.001,
        contract_size=100000.0,
        strategy=cast("ResearchStrategy", strategy),
    )


def settings() -> BacktestSettings:
    return BacktestSettings.model_validate(
        {
            "quality": {
                "maximum_gap_multiple": 3,
                "reject_history_gaps": False,
                "maximum_data_age_hours": 24,
            },
            "backtest": {
                "initial_balance": 10000.0,
                "minimum_history_bars": 3,
                "risk_per_trade_percent": 1.0,
                "slippage_points": 0.0,
                "maximum_holding_bars": 10,
                "commission_per_lot_round_turn": 0.0,
                "conservative_same_bar_exit": True,
            },
        }
    )


def active_record() -> PendingOrderRecord:
    return PendingOrderRecord(
        plan=pending_plan(),
        state=PendingOrderState.ACTIVE,
        created_at=NOW,
        updated_at=NOW,
    )


def test_pending_backtest_creates_and_expires_plan(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    planned = [pending_plan(), None, None, None, None, None]
    monkeypatch.setattr(historical, "validate_history", Mock())
    monkeypatch.setattr(historical, "plan_pending_order", Mock(side_effect=planned))
    monkeypatch.setattr(
        historical,
        "evaluate_pending_bar",
        Mock(
            return_value=PendingEvaluation(
                record=PendingOrderRecord(
                    plan=pending_plan(),
                    state=PendingOrderState.EXPIRED,
                    created_at=NOW,
                    updated_at=NOW,
                    age_bars=3,
                    reason="maximum_wait_bars_reached",
                ),
                changed=True,
            )
        ),
    )
    monkeypatch.setattr(historical, "calculate_metrics", Mock(return_value=((), Mock())))

    outcome = historical.run_pending_backtest(request(), settings(), Mock())

    assert outcome.diagnostics.plans_created == 1
    assert outcome.diagnostics.plans_expired == 1
    assert outcome.diagnostics.expiration_rate_percent == 100.0
    assert outcome.diagnostics.trigger_rate_percent == 0.0


def test_pending_backtest_triggers_and_closes_trade(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    triggered = PendingOrderRecord(
        plan=pending_plan(),
        state=PendingOrderState.TRIGGERED,
        created_at=NOW,
        updated_at=NOW,
        age_bars=1,
        triggered_at=NOW + timedelta(minutes=5),
        triggered_price=101.0,
        reason="trigger_price_reached",
    )
    monkeypatch.setattr(historical, "validate_history", Mock())
    monkeypatch.setattr(
        historical,
        "plan_pending_order",
        Mock(side_effect=[pending_plan(), None, None, None, None, None]),
    )
    monkeypatch.setattr(
        historical,
        "evaluate_pending_bar",
        Mock(return_value=PendingEvaluation(record=triggered, changed=True)),
    )
    monkeypatch.setattr(historical, "_volume", Mock(return_value=(0.1, 100.0)))
    monkeypatch.setattr(
        historical,
        "_exit_price",
        Mock(return_value=(104.0, Mock())),
    )
    monkeypatch.setattr(
        historical,
        "_close",
        Mock(return_value=SimpleNamespace(net_pnl=25.0)),
    )
    monkeypatch.setattr(historical, "calculate_metrics", Mock(return_value=((), Mock())))
    monkeypatch.setattr(
        historical,
        "BacktestResult",
        lambda symbol, trades, equity, metrics: SimpleNamespace(
            symbol=symbol,
            trades=trades,
            equity=equity,
            metrics=metrics,
        ),
    )

    outcome = historical.run_pending_backtest(request(), settings(), Mock())

    assert outcome.diagnostics.plans_created == 1
    assert outcome.diagnostics.plans_triggered == 1
    assert outcome.diagnostics.average_wait_bars == 1.0
    assert outcome.diagnostics.trigger_rate_percent == 100.0
    assert len(outcome.result.trades) == 1


def test_pending_diagnostic_rates_are_zero_without_plans() -> None:
    diagnostics = historical.PendingBacktestDiagnostics(0, 0, 0, 0.0)
    assert diagnostics.trigger_rate_percent == 0.0
    assert diagnostics.expiration_rate_percent == 0.0

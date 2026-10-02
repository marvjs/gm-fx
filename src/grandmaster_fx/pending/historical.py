"""Chronological pending-entry backtesting."""

from dataclasses import dataclass
from datetime import UTC, datetime

from grandmaster_fx.backtesting.engine import (
    BacktestInput,
    CloseContext,
    OpenTrade,
    _close,
    _exit_price,
    _volume,
)
from grandmaster_fx.backtesting.metrics import calculate_metrics
from grandmaster_fx.backtesting.models import BacktestResult, ExitReason
from grandmaster_fx.backtesting.quality import validate_history
from grandmaster_fx.config.backtest import BacktestSettings
from grandmaster_fx.config.pending_orders import PendingOrderSettings
from grandmaster_fx.pending.models import PendingOrderRecord, PendingOrderState
from grandmaster_fx.pending.planner import plan_pending_order
from grandmaster_fx.pending.simulator import evaluate_pending_bar


@dataclass(frozen=True, slots=True)
class PendingBacktestDiagnostics:
    plans_created: int
    plans_triggered: int
    plans_expired: int
    average_wait_bars: float

    @property
    def trigger_rate_percent(self) -> float:
        return self.plans_triggered / self.plans_created * 100 if self.plans_created else 0.0

    @property
    def expiration_rate_percent(self) -> float:
        return self.plans_expired / self.plans_created * 100 if self.plans_created else 0.0


@dataclass(frozen=True, slots=True)
class PendingBacktestResult:
    result: BacktestResult
    diagnostics: PendingBacktestDiagnostics


def run_pending_backtest(
    request: BacktestInput, backtest: BacktestSettings, pending: PendingOrderSettings
) -> PendingBacktestResult:
    validate_history(
        request.bars,
        request.timeframe,
        backtest.quality.maximum_gap_multiple,
        reject_gaps=backtest.quality.reject_history_gaps,
    )
    balance = backtest.backtest.initial_balance
    trades = []
    active = None
    opened = None
    created = triggered = expired = wait = 0
    start = max(backtest.backtest.minimum_history_bars, request.strategy.minimum_bars)
    for index in range(start, len(request.bars)):
        bar = request.bars[index]
        if opened is not None:
            outcome = _exit_price(
                opened,
                bar,
                backtest.backtest.slippage_points,
                request.point,
                backtest.backtest.maximum_holding_bars,
                index,
            )
            if outcome is not None:
                price, reason = outcome
                trade = _close(
                    opened,
                    CloseContext(
                        request.symbol,
                        bar,
                        index,
                        price,
                        reason,
                        request.contract_size,
                        backtest.backtest.commission_per_lot_round_turn,
                    ),
                )
                trades.append(trade)
                balance += trade.net_pnl
                opened = None
            continue
        if active is not None:
            active = evaluate_pending_bar(active, bar).record
            if active.state is PendingOrderState.EXPIRED:
                expired += 1
                active = None
            elif active.state is PendingOrderState.TRIGGERED:
                triggered += 1
                wait += active.age_bars
                entry = active.triggered_price or active.plan.trigger_price
                volume, risk = _volume(
                    balance,
                    backtest.backtest.risk_per_trade_percent,
                    entry,
                    active.plan.stop_loss,
                    request.contract_size,
                )
                opened = OpenTrade(
                    active.plan.signal,
                    index,
                    bar.time,
                    entry,
                    active.plan.stop_loss,
                    active.plan.take_profit,
                    volume,
                    risk,
                )
                active = None
            continue
        decision = request.strategy.evaluate(request.symbol, request.bars[:index], request.point)
        plan = plan_pending_order(
            request.strategy.identifier,
            request.symbol,
            request.timeframe,
            decision,
            request.bars[:index],
            pending,
        )
        if plan is not None:
            now = datetime.now(UTC)
            active = PendingOrderRecord(plan, PendingOrderState.ACTIVE, now, now)
            created += 1
    if opened is not None:
        final = request.bars[-1]
        trades.append(
            _close(
                opened,
                CloseContext(
                    request.symbol,
                    final,
                    len(request.bars) - 1,
                    final.close,
                    ExitReason.END_OF_DATA,
                    request.contract_size,
                    backtest.backtest.commission_per_lot_round_turn,
                ),
            )
        )
    equity, metrics = calculate_metrics(backtest.backtest.initial_balance, trades)
    return PendingBacktestResult(
        BacktestResult(request.symbol, tuple(trades), equity, metrics),
        PendingBacktestDiagnostics(
            created, triggered, expired, wait / triggered if triggered else 0.0
        ),
    )

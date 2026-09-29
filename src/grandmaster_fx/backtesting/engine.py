"""No-lookahead chronological bar backtesting engine."""

from dataclasses import dataclass
from datetime import datetime

from grandmaster_fx.backtesting.metrics import calculate_metrics
from grandmaster_fx.backtesting.models import BacktestResult, ExitReason, SimulatedTrade
from grandmaster_fx.backtesting.quality import validate_history
from grandmaster_fx.config.backtest import BacktestSettings
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.strategies import Signal
from grandmaster_fx.strategies.models import StrategyDecision
from grandmaster_fx.strategies.protocol import IndexedResearchStrategy, ResearchStrategy


@dataclass(frozen=True, slots=True)
class BacktestInput:
    """Static market and strategy inputs for one simulation."""

    symbol: str
    bars: list[Bar]
    timeframe: Timeframe
    point: float
    contract_size: float
    strategy: ResearchStrategy


@dataclass(slots=True)
class OpenTrade:
    """Mutable state for one simulated open position."""

    signal: Signal
    entry_index: int
    entry_time: datetime
    entry: float
    stop: float
    target: float
    volume: float
    risk_cash: float


@dataclass(frozen=True, slots=True)
class CloseContext:
    """Market and cost inputs needed to close a simulated position."""

    symbol: str
    bar: Bar
    index: int
    price: float
    reason: ExitReason
    contract_size: float
    commission: float


def _volume(
    balance: float, risk_percent: float, entry: float, stop: float, contract_size: float
) -> tuple[float, float]:
    risk_cash = balance * risk_percent / 100
    distance = abs(entry - stop)
    if distance <= 0:
        message = "stop distance must be positive"
        raise ValueError(message)
    raw = risk_cash / (distance * contract_size)
    volume = max(0.01, int(raw * 100) / 100)
    return volume, risk_cash


def _exit_price(
    trade: OpenTrade,
    bar: Bar,
    slippage: float,
    point: float,
    maximum_holding: int,
    index: int,
) -> tuple[float, ExitReason] | None:
    if trade.signal is Signal.BUY:
        if bar.low <= trade.stop:
            return trade.stop - slippage * point, ExitReason.STOP_LOSS
        if bar.high >= trade.target:
            return trade.target - slippage * point, ExitReason.TAKE_PROFIT
    else:
        if bar.high >= trade.stop:
            return trade.stop + slippage * point, ExitReason.STOP_LOSS
        if bar.low <= trade.target:
            return trade.target + slippage * point, ExitReason.TAKE_PROFIT
    if index - trade.entry_index >= maximum_holding:
        return bar.close, ExitReason.TIME_STOP
    return None


def _close(trade: OpenTrade, context: CloseContext) -> SimulatedTrade:
    direction = 1 if trade.signal is Signal.BUY else -1
    gross = (context.price - trade.entry) * direction * context.contract_size * trade.volume
    costs = context.commission * trade.volume
    net = gross - costs
    return SimulatedTrade(
        symbol=context.symbol,
        signal=trade.signal,
        entry_time=trade.entry_time,
        exit_time=context.bar.time,
        entry=trade.entry,
        exit=context.price,
        stop_loss=trade.stop,
        take_profit=trade.target,
        volume=trade.volume,
        gross_pnl=gross,
        costs=costs,
        net_pnl=net,
        return_r=net / trade.risk_cash,
        holding_bars=context.index - trade.entry_index,
        exit_reason=context.reason,
    )


def _close_context(
    request: BacktestInput,
    settings: BacktestSettings,
    bar: Bar,
    index: int,
    price: float,
    reason: ExitReason,
) -> CloseContext:
    return CloseContext(
        symbol=request.symbol,
        bar=bar,
        index=index,
        price=price,
        reason=reason,
        contract_size=request.contract_size,
        commission=settings.backtest.commission_per_lot_round_turn,
    )


def _evaluate_strategy(
    request: BacktestInput, index: int, prepared: object | None = None
) -> StrategyDecision:
    """Evaluate through indexed context when supported, otherwise use compatibility mode."""
    if isinstance(request.strategy, IndexedResearchStrategy) and prepared is not None:
        return request.strategy.evaluate_at(
            request.symbol, request.bars, index - 1, request.point, prepared
        )
    return request.strategy.evaluate(request.symbol, request.bars[:index], request.point)


def _open_trade(
    request: BacktestInput,
    settings: BacktestSettings,
    balance: float,
    index: int,
    prepared: object | None = None,
) -> OpenTrade | None:
    decision = _evaluate_strategy(request, index, prepared)
    if not (
        decision.actionable
        and decision.entry is not None
        and decision.stop_loss is not None
        and decision.take_profit is not None
    ):
        return None
    adjustment = settings.backtest.slippage_points * request.point
    entry = request.bars[index].open + (
        adjustment if decision.signal is Signal.BUY else -adjustment
    )
    volume, risk = _volume(
        balance,
        settings.backtest.risk_per_trade_percent,
        entry,
        decision.stop_loss,
        request.contract_size,
    )
    return OpenTrade(
        signal=decision.signal,
        entry_index=index,
        entry_time=request.bars[index].time,
        entry=entry,
        stop=decision.stop_loss,
        target=decision.take_profit,
        volume=volume,
        risk_cash=risk,
    )


def run_backtest(request: BacktestInput, settings: BacktestSettings) -> BacktestResult:
    """Run a chronological single-position simulation."""
    validate_history(
        request.bars,
        request.timeframe,
        settings.quality.maximum_gap_multiple,
        reject_gaps=settings.quality.reject_history_gaps,
    )
    balance = settings.backtest.initial_balance
    trades: list[SimulatedTrade] = []
    opened: OpenTrade | None = None
    start = max(settings.backtest.minimum_history_bars, request.strategy.minimum_bars)
    prepared = (
        request.strategy.prepare(request.bars)
        if isinstance(request.strategy, IndexedResearchStrategy)
        else None
    )
    for index in range(start, len(request.bars)):
        bar = request.bars[index]
        if opened is not None:
            outcome = _exit_price(
                opened,
                bar,
                settings.backtest.slippage_points,
                request.point,
                settings.backtest.maximum_holding_bars,
                index,
            )
            if outcome is not None:
                price, reason = outcome
                trade = _close(opened, _close_context(request, settings, bar, index, price, reason))
                trades.append(trade)
                balance += trade.net_pnl
                opened = None
        if opened is None:
            opened = _open_trade(request, settings, balance, index, prepared)
    if opened is not None:
        final = request.bars[-1]
        context = _close_context(
            request,
            settings,
            final,
            len(request.bars) - 1,
            final.close,
            ExitReason.END_OF_DATA,
        )
        trades.append(_close(opened, context))
    equity, metrics = calculate_metrics(settings.backtest.initial_balance, trades)
    return BacktestResult(request.symbol, tuple(trades), equity, metrics)

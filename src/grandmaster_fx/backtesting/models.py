"""Backtest trades, metrics, and results."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from grandmaster_fx.strategies.models import Signal


class ExitReason(StrEnum):
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"
    TIME_STOP = "time_stop"
    END_OF_DATA = "end_of_data"


@dataclass(frozen=True, slots=True)
class SimulatedTrade:
    symbol: str
    signal: Signal
    entry_time: datetime
    exit_time: datetime
    entry: float
    exit: float
    stop_loss: float
    take_profit: float
    volume: float
    gross_pnl: float
    costs: float
    net_pnl: float
    return_r: float
    holding_bars: int
    exit_reason: ExitReason

    def __post_init__(self) -> None:
        """Reject impossible trade timelines and negative holding periods."""
        if self.exit_time < self.entry_time:
            message = "trade exit_time cannot precede entry_time"
            raise ValueError(message)
        if self.holding_bars < 0:
            message = "trade holding_bars cannot be negative"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class BacktestMetrics:
    initial_balance: float
    final_balance: float
    net_profit: float
    total_return_percent: float
    maximum_drawdown_percent: float
    trade_count: int
    wins: int
    losses: int
    win_rate_percent: float
    profit_factor: float | None
    expectancy: float
    average_win: float
    average_loss: float
    payoff_ratio: float | None
    maximum_consecutive_losses: int


@dataclass(frozen=True, slots=True)
class BacktestResult:
    symbol: str
    trades: tuple[SimulatedTrade, ...]
    equity_curve: tuple[float, ...]
    metrics: BacktestMetrics

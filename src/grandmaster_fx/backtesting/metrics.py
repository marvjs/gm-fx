"""Deterministic backtest performance metrics."""

from grandmaster_fx.backtesting.models import BacktestMetrics, SimulatedTrade


def calculate_metrics(
    initial_balance: float, trades: list[SimulatedTrade]
) -> tuple[tuple[float, ...], BacktestMetrics]:
    equity = [initial_balance]
    wins = []
    losses = []
    max_consecutive = consecutive = 0
    for trade in trades:
        equity.append(equity[-1] + trade.net_pnl)
        if trade.net_pnl > 0:
            wins.append(trade.net_pnl)
            consecutive = 0
        else:
            losses.append(trade.net_pnl)
            consecutive += 1
            max_consecutive = max(max_consecutive, consecutive)
    peaks = []
    peak = initial_balance
    maximum_drawdown = 0.0
    for value in equity:
        peak = max(peak, value)
        peaks.append(peak)
        maximum_drawdown = max(maximum_drawdown, (peak - value) / peak * 100 if peak else 0.0)
    gross_profit = sum(wins)
    gross_loss = abs(sum(losses))
    count = len(trades)
    final = equity[-1]
    average_win = gross_profit / len(wins) if wins else 0.0
    average_loss = gross_loss / len(losses) if losses else 0.0
    profit_factor = gross_profit / gross_loss if gross_loss else None
    payoff = average_win / average_loss if average_loss else None
    metrics = BacktestMetrics(
        initial_balance,
        final,
        final - initial_balance,
        (final / initial_balance - 1) * 100,
        maximum_drawdown,
        count,
        len(wins),
        len(losses),
        len(wins) / count * 100 if count else 0.0,
        profit_factor,
        (final - initial_balance) / count if count else 0.0,
        average_win,
        average_loss,
        payoff,
        max_consecutive,
    )
    return tuple(equity), metrics

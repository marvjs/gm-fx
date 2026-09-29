"""Backtest trade attribution and cost analysis."""

from collections import defaultdict
from collections.abc import Callable

from grandmaster_fx.backtesting.models import BacktestResult, SimulatedTrade
from grandmaster_fx.research.models import CostSummary, ResearchAnalysis, TradeBreakdown


def _breakdowns(
    trades: tuple[SimulatedTrade, ...], key: Callable[[SimulatedTrade], str]
) -> tuple[TradeBreakdown, ...]:
    groups: dict[str, list[SimulatedTrade]] = defaultdict(list)
    for trade in trades:
        groups[key(trade)].append(trade)
    rows: list[TradeBreakdown] = []
    for name, items in sorted(groups.items()):
        net = sum(item.net_pnl for item in items)
        wins = sum(item.net_pnl > 0 for item in items)
        rows.append(
            TradeBreakdown(
                key=name,
                trades=len(items),
                net_profit=net,
                win_rate_percent=wins / len(items) * 100,
                expectancy=net / len(items),
            )
        )
    return tuple(rows)


def analyze_result(result: BacktestResult) -> ResearchAnalysis:
    """Attribute performance by direction, exit, hour, weekday, and costs."""
    trades = result.trades
    gross = sum(trade.gross_pnl for trade in trades)
    costs = sum(trade.costs for trade in trades)
    net = sum(trade.net_pnl for trade in trades)
    drag = costs / abs(gross) * 100 if gross else 0.0
    return ResearchAnalysis(
        result=result,
        by_signal=_breakdowns(trades, lambda trade: trade.signal.value),
        by_exit_reason=_breakdowns(trades, lambda trade: trade.exit_reason.value),
        by_hour=_breakdowns(trades, lambda trade: f"{trade.entry_time.hour:02d}:00"),
        by_weekday=_breakdowns(trades, lambda trade: trade.entry_time.strftime("%A")),
        costs=CostSummary(gross, costs, net, drag),
    )

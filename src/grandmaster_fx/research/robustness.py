"""Walk-forward, sensitivity, ablation, and portfolio research."""

from collections.abc import Callable
from dataclasses import dataclass, replace

from grandmaster_fx.backtesting.engine import BacktestInput, run_backtest
from grandmaster_fx.backtesting.models import BacktestResult, SimulatedTrade
from grandmaster_fx.config.backtest import BacktestSettings
from grandmaster_fx.config.research import ResearchSettings
from grandmaster_fx.research.models import SensitivityRun, WalkForwardFold
from grandmaster_fx.research.splits import anchored_windows
from grandmaster_fx.strategies.models import Signal

MINIMUM_PROFITABLE_FOLD_PERCENT = 75.0
MINIMUM_STABLE_PROFIT_FACTOR = 1.0
SHORT_HOLDING_BAR_LIMIT = 5


@dataclass(frozen=True, slots=True)
class StabilitySummary:
    """Aggregate robustness statistics across out-of-sample folds."""

    folds: int
    profitable_folds: int
    profitable_fold_percent: float
    aggregate_trades: int
    aggregate_net_profit: float
    worst_drawdown_percent: float
    average_profit_factor: float
    stable: bool


@dataclass(frozen=True, slots=True)
class AblationResult:
    """One diagnostic subset of a completed backtest."""

    label: str
    trades: int
    net_profit: float
    expectancy: float
    win_rate_percent: float


def _metrics_from_results(results: tuple[BacktestResult, ...]) -> StabilitySummary:
    """Summarize fold stability without combining overlapping equity curves."""
    count = len(results)
    profitable = sum(item.metrics.net_profit > 0 for item in results)
    factors = [item.metrics.profit_factor or 0.0 for item in results]
    trades = sum(item.metrics.trade_count for item in results)
    net = sum(item.metrics.net_profit for item in results)
    worst_drawdown = max((item.metrics.maximum_drawdown_percent for item in results), default=0.0)
    average_factor = sum(factors) / count if count else 0.0
    profitable_percent = profitable / count * 100 if count else 0.0
    return StabilitySummary(
        folds=count,
        profitable_folds=profitable,
        profitable_fold_percent=profitable_percent,
        aggregate_trades=trades,
        aggregate_net_profit=net,
        worst_drawdown_percent=worst_drawdown,
        average_profit_factor=average_factor,
        stable=count > 0
        and profitable_percent >= MINIMUM_PROFITABLE_FOLD_PERCENT
        and average_factor >= MINIMUM_STABLE_PROFIT_FACTOR,
    )


def walk_forward(
    request: BacktestInput,
    backtest: BacktestSettings,
    research: ResearchSettings,
) -> tuple[tuple[WalkForwardFold, ...], StabilitySummary]:
    """Run anchored, non-overlapping out-of-sample folds."""
    windows = anchored_windows(
        len(request.bars),
        research.walk_forward.folds,
        research.walk_forward.minimum_train_bars,
        research.walk_forward.minimum_test_bars,
    )
    folds: list[WalkForwardFold] = []
    for number, (train_start, train_end, test_start, test_end) in enumerate(windows, 1):
        test_request = replace(request, bars=request.bars[test_start:test_end])
        result = run_backtest(test_request, backtest)
        folds.append(WalkForwardFold(number, train_start, train_end, test_start, test_end, result))
    completed = tuple(folds)
    return completed, _metrics_from_results(tuple(item.result for item in completed))


def sensitivity_runs(
    request: BacktestInput,
    settings: BacktestSettings,
    research: ResearchSettings,
) -> tuple[SensitivityRun, ...]:
    """Stress commission and slippage assumptions independently."""
    runs: list[SensitivityRun] = []
    for slippage in research.sensitivity.slippage_points:
        configured = settings.model_copy(
            update={"backtest": settings.backtest.model_copy(update={"slippage_points": slippage})}
        )
        runs.append(SensitivityRun(f"slippage={slippage:g}", run_backtest(request, configured)))
    for commission in research.sensitivity.commission_per_lot:
        configured = settings.model_copy(
            update={
                "backtest": settings.backtest.model_copy(
                    update={"commission_per_lot_round_turn": commission}
                )
            }
        )
        runs.append(SensitivityRun(f"commission={commission:g}", run_backtest(request, configured)))
    return tuple(runs)


def _ablation(
    label: str,
    trades: tuple[SimulatedTrade, ...],
    predicate: Callable[[SimulatedTrade], bool],
) -> AblationResult:
    selected = [trade for trade in trades if predicate(trade)]
    net = sum(trade.net_pnl for trade in selected)
    wins = sum(trade.net_pnl > 0 for trade in selected)
    count = len(selected)
    return AblationResult(
        label=label,
        trades=count,
        net_profit=net,
        expectancy=net / count if count else 0.0,
        win_rate_percent=wins / count * 100 if count else 0.0,
    )


def ablations(result: BacktestResult) -> tuple[AblationResult, ...]:
    """Return diagnostic direction and holding-period subsets."""
    trades = result.trades
    return (
        _ablation("BUY", trades, lambda trade: trade.signal is Signal.BUY),
        _ablation("SELL", trades, lambda trade: trade.signal is Signal.SELL),
        _ablation(
            "holding<=5", trades, lambda trade: trade.holding_bars <= SHORT_HOLDING_BAR_LIMIT
        ),
        _ablation("holding>5", trades, lambda trade: trade.holding_bars > SHORT_HOLDING_BAR_LIMIT),
    )


def portfolio_summary(results: tuple[BacktestResult, ...]) -> StabilitySummary:
    """Summarize independent symbol results without implying diversification."""
    return _metrics_from_results(results)

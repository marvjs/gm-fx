"""Immutable strategy research reports."""

from dataclasses import dataclass

from grandmaster_fx.backtesting.models import BacktestResult


@dataclass(frozen=True, slots=True)
class TradeBreakdown:
    """Aggregated trade performance for one category."""

    key: str
    trades: int
    net_profit: float
    win_rate_percent: float
    expectancy: float


@dataclass(frozen=True, slots=True)
class CostSummary:
    """Gross and cost contribution to simulated performance."""

    gross_profit: float
    total_costs: float
    net_profit: float
    cost_drag_percent: float


@dataclass(frozen=True, slots=True)
class ResearchAnalysis:
    """Complete diagnostic analysis of one backtest result."""

    result: BacktestResult
    by_signal: tuple[TradeBreakdown, ...]
    by_exit_reason: tuple[TradeBreakdown, ...]
    by_hour: tuple[TradeBreakdown, ...]
    by_weekday: tuple[TradeBreakdown, ...]
    costs: CostSummary


@dataclass(frozen=True, slots=True)
class ValidationCheck:
    """One machine-readable validation threshold outcome."""

    name: str
    passed: bool
    actual: float
    required: float


@dataclass(frozen=True, slots=True)
class ValidationReport:
    """Out-of-sample validation verdict and checks."""

    passed: bool
    checks: tuple[ValidationCheck, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WalkForwardFold:
    """One anchored training and test window."""

    number: int
    train_start: int
    train_end: int
    test_start: int
    test_end: int
    result: BacktestResult


@dataclass(frozen=True, slots=True)
class SensitivityRun:
    """One cost-sensitivity simulation result."""

    label: str
    result: BacktestResult

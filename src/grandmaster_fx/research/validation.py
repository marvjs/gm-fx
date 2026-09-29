"""Out-of-sample strategy validation thresholds."""

from grandmaster_fx.backtesting.models import BacktestResult
from grandmaster_fx.config.research import ValidationThresholds
from grandmaster_fx.research.models import ValidationCheck, ValidationReport

LONG_LOSING_STREAK_THRESHOLD = 8


def _check(name: str, actual: float, required: float, *, maximum: bool = False) -> ValidationCheck:
    passed = actual <= required if maximum else actual >= required
    return ValidationCheck(name, passed, actual, required)


def validate_result(result: BacktestResult, thresholds: ValidationThresholds) -> ValidationReport:
    """Evaluate an out-of-sample result without optimizing it."""
    metrics = result.metrics
    profit_factor = metrics.profit_factor or 0.0
    checks = (
        _check("minimum_trades", float(metrics.trade_count), float(thresholds.minimum_trades)),
        _check("profit_factor", profit_factor, thresholds.minimum_profit_factor),
        _check("expectancy", metrics.expectancy, thresholds.minimum_expectancy),
        _check(
            "maximum_drawdown_percent",
            metrics.maximum_drawdown_percent,
            thresholds.maximum_drawdown_percent,
            maximum=True,
        ),
        _check(
            "out_of_sample_return_percent",
            metrics.total_return_percent,
            thresholds.minimum_out_of_sample_return_percent,
        ),
    )
    warnings: list[str] = []
    if metrics.trade_count < thresholds.minimum_trades:
        warnings.append("insufficient_trade_count")
    if profit_factor < 1.0:
        warnings.append("negative_edge")
    if metrics.maximum_consecutive_losses >= LONG_LOSING_STREAK_THRESHOLD:
        warnings.append("long_losing_streak")
    return ValidationReport(
        passed=all(item.passed for item in checks),
        checks=checks,
        warnings=tuple(warnings),
    )

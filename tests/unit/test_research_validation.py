"""Research validation tests."""

from grandmaster_fx.backtesting.models import BacktestMetrics, BacktestResult
from grandmaster_fx.config.research import ValidationThresholds
from grandmaster_fx.research.validation import validate_result


def result(
    *, trades: int, profit_factor: float, expectancy: float, drawdown: float, return_percent: float
) -> BacktestResult:
    metrics = BacktestMetrics(
        10000,
        10000 * (1 + return_percent / 100),
        return_percent * 100,
        return_percent,
        drawdown,
        trades,
        trades // 2,
        trades - trades // 2,
        50,
        profit_factor,
        expectancy,
        10,
        10,
        1,
        3,
    )
    return BacktestResult("EURUSDm", (), (10000,), metrics)


def thresholds() -> ValidationThresholds:
    return ValidationThresholds(
        in_sample_fraction=0.7,
        minimum_trades=30,
        minimum_profit_factor=1.1,
        minimum_expectancy=0,
        maximum_drawdown_percent=15,
        minimum_out_of_sample_return_percent=0,
    )


def test_passing_result() -> None:
    report = validate_result(
        result(trades=50, profit_factor=1.2, expectancy=2, drawdown=10, return_percent=5),
        thresholds(),
    )
    assert report.passed
    assert not report.warnings


def test_failing_result_has_warnings() -> None:
    report = validate_result(
        result(trades=10, profit_factor=0.8, expectancy=-1, drawdown=20, return_percent=-5),
        thresholds(),
    )
    assert not report.passed
    assert "insufficient_trade_count" in report.warnings
    assert "negative_edge" in report.warnings

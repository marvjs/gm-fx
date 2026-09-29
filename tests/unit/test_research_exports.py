"""Research export tests."""

import json
from datetime import UTC, datetime
from pathlib import Path

from grandmaster_fx.backtesting.metrics import calculate_metrics
from grandmaster_fx.backtesting.models import BacktestResult, ExitReason, SimulatedTrade
from grandmaster_fx.config.research import ValidationThresholds
from grandmaster_fx.research.analysis import analyze_result
from grandmaster_fx.research.exports import export_research
from grandmaster_fx.research.validation import validate_result
from grandmaster_fx.strategies.models import Signal


def test_exports_are_machine_readable(tmp_path: Path) -> None:
    now = datetime(2026, 1, 1, tzinfo=UTC)
    trade = SimulatedTrade(
        "EURUSDm",
        Signal.BUY,
        now,
        now,
        1,
        1.1,
        0.9,
        1.1,
        0.1,
        100,
        1,
        99,
        1,
        1,
        ExitReason.TAKE_PROFIT,
    )
    equity, metrics = calculate_metrics(1000, [trade])
    result = BacktestResult("EURUSDm", (trade,), equity, metrics)
    analysis = analyze_result(result)
    thresholds = ValidationThresholds(
        in_sample_fraction=0.7,
        minimum_trades=1,
        minimum_profit_factor=0.1,
        minimum_expectancy=0,
        maximum_drawdown_percent=50,
        minimum_out_of_sample_return_percent=0,
    )
    validation = validate_result(result, thresholds)
    ledger, summary, verdict = export_research(analysis, validation, tmp_path)
    assert ledger.is_file()
    assert json.loads(summary.read_text())["symbol"] == "EURUSDm"
    exported = json.loads(verdict.read_text())
    assert exported["passed"] is validation.passed
    assert exported["checks"]

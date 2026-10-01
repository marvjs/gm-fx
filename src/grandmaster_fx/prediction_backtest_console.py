"""Prediction-gate backtest diagnostics."""

from rich.table import Table

from grandmaster_fx.console import console
from grandmaster_fx.predictions.backtest import PredictionBacktestReport


def render_prediction_backtest(report: PredictionBacktestReport) -> None:
    table = Table(title="Prediction Gate Diagnostics", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Primary signals", str(report.primary_signals))
    table.add_row("Accepted signals", str(report.accepted_signals))
    table.add_row("Rejected signals", str(report.rejected_signals))
    for reason, count in report.rejection_reasons.items():
        table.add_row(f"Rejected: {reason}", str(count))
    for regime, count in report.regimes.items():
        table.add_row(f"Regime candles: {regime}", str(count))
    console.print(table)

"""Rich rendering for strategy research reports."""

from rich.panel import Panel
from rich.table import Table

from grandmaster_fx.console import console
from grandmaster_fx.research.models import ResearchAnalysis, ValidationReport


def render_research(analysis: ResearchAnalysis, validation: ValidationReport) -> None:
    """Render research diagnostics and an explicit pass/fail verdict."""
    verdict = "PASS" if validation.passed else "FAIL"
    style = "green" if validation.passed else "red"
    console.print(Panel.fit(f"Research validation: {verdict}", style=style))
    metrics = analysis.result.metrics
    table = Table(title=f"Research | {analysis.result.symbol}", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    rows = (
        ("Trades", str(metrics.trade_count)),
        ("Return", f"{metrics.total_return_percent:.2f}%"),
        ("Maximum drawdown", f"{metrics.maximum_drawdown_percent:.2f}%"),
        (
            "Profit factor",
            "N/A" if metrics.profit_factor is None else f"{metrics.profit_factor:.3f}",
        ),
        ("Expectancy", f"{metrics.expectancy:.2f}"),
        ("Gross P/L", f"{analysis.costs.gross_profit:.2f}"),
        ("Costs", f"{analysis.costs.total_costs:.2f}"),
        ("Cost drag", f"{analysis.costs.cost_drag_percent:.2f}%"),
        ("Warnings", ", ".join(validation.warnings) or "None"),
    )
    for row in rows:
        table.add_row(*row)
    console.print(table)
    console.print("[dim]Research only. No order was constructed or submitted.[/dim]")

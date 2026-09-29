"""Rich rendering for robustness research."""

from rich.panel import Panel
from rich.table import Table

from grandmaster_fx.console import console
from grandmaster_fx.research.models import SensitivityRun, WalkForwardFold
from grandmaster_fx.research.robustness import AblationResult, StabilitySummary


def render_robustness(
    symbol: str,
    folds: tuple[WalkForwardFold, ...],
    stability: StabilitySummary,
    sensitivity: tuple[SensitivityRun, ...],
    ablation: tuple[AblationResult, ...],
) -> None:
    """Render walk-forward stability, cost sensitivity, and ablations."""
    verdict = "STABLE" if stability.stable else "UNSTABLE"
    style = "green" if stability.stable else "red"
    console.print(Panel.fit(f"{symbol} robustness: {verdict}", style=style))
    fold_table = Table(title="Walk-forward folds")
    for name in ("Fold", "Trades", "Return", "Drawdown", "Profit factor"):
        fold_table.add_column(name, justify="right")
    for fold in folds:
        metrics = fold.result.metrics
        fold_table.add_row(
            str(fold.number),
            str(metrics.trade_count),
            f"{metrics.total_return_percent:.2f}%",
            f"{metrics.maximum_drawdown_percent:.2f}%",
            "N/A" if metrics.profit_factor is None else f"{metrics.profit_factor:.3f}",
        )
    console.print(fold_table)
    sensitivity_table = Table(title="Cost sensitivity")
    sensitivity_table.add_column("Scenario")
    sensitivity_table.add_column("Return", justify="right")
    sensitivity_table.add_column("Profit factor", justify="right")
    for sensitivity_item in sensitivity:
        metrics = sensitivity_item.result.metrics
        sensitivity_table.add_row(
            sensitivity_item.label,
            f"{metrics.total_return_percent:.2f}%",
            "N/A" if metrics.profit_factor is None else f"{metrics.profit_factor:.3f}",
        )
    console.print(sensitivity_table)
    ablation_table = Table(title="Diagnostic ablations")
    for name in ("Subset", "Trades", "Net P/L", "Expectancy", "Win rate"):
        ablation_table.add_column(name, justify="right")
    for ablation_item in ablation:
        ablation_table.add_row(
            ablation_item.label,
            str(ablation_item.trades),
            f"{ablation_item.net_profit:.2f}",
            f"{ablation_item.expectancy:.2f}",
            f"{ablation_item.win_rate_percent:.2f}%",
        )
    console.print(ablation_table)
    console.print("[dim]Research only. No order was constructed or submitted.[/dim]")

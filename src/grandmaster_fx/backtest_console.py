"""Rich backtest result rendering."""

from rich.table import Table

from grandmaster_fx.backtesting.models import BacktestResult
from grandmaster_fx.console import console


def render_backtest(result: BacktestResult) -> None:
    m = result.metrics
    table = Table(title=f"Backtest | {result.symbol}", show_header=False)
    table.add_column("Metric", style="bold")
    table.add_column("Value", justify="right")
    rows = (
        ("Trades", str(m.trade_count)),
        ("Final balance", f"{m.final_balance:,.2f}"),
        ("Net profit", f"{m.net_profit:,.2f}"),
        ("Return", f"{m.total_return_percent:.2f}%"),
        ("Maximum drawdown", f"{m.maximum_drawdown_percent:.2f}%"),
        ("Win rate", f"{m.win_rate_percent:.2f}%"),
        ("Profit factor", "N/A" if m.profit_factor is None else f"{m.profit_factor:.3f}"),
        ("Expectancy", f"{m.expectancy:.2f}"),
        ("Maximum consecutive losses", str(m.maximum_consecutive_losses)),
    )
    for row in rows:
        table.add_row(*row)
    console.print(table)
    console.print("[dim]Historical simulation only. No order was submitted.[/dim]")

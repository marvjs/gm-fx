"""Rich rendering for numerical indicator snapshots."""

from rich.table import Table

from grandmaster_fx.console import console
from grandmaster_fx.indicators.snapshot import IndicatorSnapshot


def render_indicator_snapshot(
    pair: str, broker_symbol: str, timeframe: str, snapshot: IndicatorSnapshot
) -> None:
    """Render the latest indicator values."""
    table = Table(title=f"{pair.upper()} | {broker_symbol} | {timeframe}", show_header=False)
    table.add_column("Indicator", style="bold")
    table.add_column("Value", justify="right")
    rows = (
        ("Close", f"{snapshot.close:.8g}"),
        ("SMA 20", f"{snapshot.sma_20:.8g}"),
        ("EMA 12", f"{snapshot.ema_12:.8g}"),
        ("EMA 26", f"{snapshot.ema_26:.8g}"),
        ("RSI 14", f"{snapshot.rsi_14:.4f}"),
        ("ATR 14", f"{snapshot.atr_14:.8g}"),
        ("ROC 10 (%)", f"{snapshot.roc_10:.6f}"),
        ("Spread (points)", str(snapshot.spread_points)),
    )
    for row in rows:
        table.add_row(*row)
    console.print(table)

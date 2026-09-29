"""Rich rendering for forex symbols."""

from rich.table import Table

from grandmaster_fx.console import console
from grandmaster_fx.domain.symbols import SymbolSnapshot


def render_symbols(symbols: list[SymbolSnapshot]) -> None:
    table = Table(title=f"Eligible forex symbols ({len(symbols)})")
    for column in ("Pair", "Broker symbol", "Visible", "Spread", "Min lot", "Step", "Trade"):
        table.add_column(column)
    for item in sorted(symbols, key=lambda value: (value.identity.normalized, value.name)):
        table.add_row(
            item.identity.normalized,
            item.name,
            "Yes" if item.visible else "No",
            str(item.spread_points),
            f"{item.volume_min:g}",
            f"{item.volume_step:g}",
            "Enabled" if item.trade_enabled else "Disabled",
        )
    console.print(table)


def render_symbol(item: SymbolSnapshot) -> None:
    table = Table(title=f"{item.identity.normalized} | {item.name}", show_header=False)
    table.add_column("Property", style="bold")
    table.add_column("Value")
    rows = (
        ("Currencies", f"{item.identity.base}/{item.identity.quote}"),
        ("Description", item.description),
        ("Visible", str(item.visible)),
        ("Selected", str(item.selected)),
        ("Trade enabled", str(item.trade_enabled)),
        ("Digits", str(item.digits)),
        ("Point", f"{item.point:g}"),
        ("Spread points", str(item.spread_points)),
        ("Spread price", f"{item.spread_price:g}"),
        ("Tick size", f"{item.tick_size:g}"),
        ("Tick value", f"{item.tick_value:g}"),
        ("Contract size", f"{item.contract_size:g}"),
        ("Volume range", f"{item.volume_min:g} - {item.volume_max:g}"),
        ("Volume step", f"{item.volume_step:g}"),
        ("Stops level", str(item.stops_level)),
        ("Freeze level", str(item.freeze_level)),
    )
    for row in rows:
        table.add_row(*row)
    console.print(table)

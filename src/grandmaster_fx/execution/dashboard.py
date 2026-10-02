"""Rich dynamic terminal dashboard for demo execution."""

from datetime import UTC, datetime
from typing import Any

from rich.console import Group
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _yes_no(value: object) -> Text:
    if bool(value):
        return Text("YES", style="bold green")
    return Text("NO", style="dim")


def _number(value: object, default: float = 0.0) -> float:
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _items(value: object) -> list[object]:
    if isinstance(value, list | tuple):
        return list(value)
    return []


def _summary_cell(label: str, value: object) -> Text:
    text = Text()
    text.append(label + " ", style="bold")
    text.append(str(value))
    return text


def render_dashboard(  # noqa: C901, PLR0912, PLR0915
    payload: dict[str, object],
    *,
    strategy: str,
    timeframe: str,
    cycle_number: int,
    started_at: datetime,
    title: str = "Grandmaster FX Demo Dashboard",
) -> Group:
    """Build one complete dashboard frame from a worker-cycle payload."""
    now = datetime.now(UTC)
    uptime = int((now - started_at).total_seconds())

    summary = Table.grid(expand=True)
    for _index in range(4):
        summary.add_column(ratio=1)
    summary.add_row(
        _summary_cell("Mode", str(payload.get("profile", "? ")).upper()),
        _summary_cell("Strategy", strategy),
        _summary_cell("Timeframe", timeframe),
        _summary_cell("Cycle/Uptime", f"{cycle_number} / {uptime}s"),
    )
    summary.add_row(
        _summary_cell("Balance", f"{_number(payload.get('balance')):,.2f}"),
        _summary_cell("Equity", f"{_number(payload.get('equity')):,.2f}"),
        _summary_cell("Margin", f"{_number(payload.get('margin')):,.2f}"),
        _summary_cell("Updated UTC", now.strftime("%H:%M:%S")),
    )

    prediction_table = Table(title="Predictions", expand=True)
    headings = (
        "Symbol",
        "Regime",
        "Signal",
        "Strategy",
        "Direction",
        "Primary Reason",
        "M15",
        "M15 Reason",
        "Duplicate",
        "Accepted",
    )
    for heading in headings:
        prediction_table.add_column(heading, no_wrap=True)

    predictions = _items(payload.get("predictions"))
    if predictions:
        for raw in predictions:
            if not isinstance(raw, dict):
                continue
            prediction: dict[str, Any] = raw
            signal = str(prediction.get("signal", "?"))
            if signal == "BUY":
                signal_style = "green"
            elif signal == "SELL":
                signal_style = "red"
            else:
                signal_style = "dim"
            accepted = bool(prediction.get("accepted"))
            prediction_table.add_row(
                str(prediction.get("symbol", "?")),
                str(prediction.get("regime", "?")),
                Text(signal, style=signal_style),
                _yes_no(prediction.get("strategy_allowed")),
                _yes_no(prediction.get("direction_allowed")),
                str(prediction.get("primary_reason", "-")),
                _yes_no(prediction.get("confirmation")),
                str(prediction.get("confirmation_reason", "-")),
                _yes_no(prediction.get("duplicate")),
                Text("ACCEPT", style="bold green") if accepted else Text("WAIT", style="yellow"),
            )
    else:
        prediction_table.add_row("-", "-", "-", "-", "-", "No prediction data", "-", "-", "-", "-")

    pending_table = Table(title="Pending Orders", expand=True)
    for heading in (
        "Ticket",
        "Symbol",
        "Side",
        "Type",
        "Volume",
        "Trigger",
        "Stop",
        "Target",
        "Expiration",
    ):
        pending_table.add_column(heading, no_wrap=True)
    pending_orders = _items(payload.get("pending_orders"))
    if pending_orders:
        for raw in pending_orders:
            if isinstance(raw, dict):
                pending_table.add_row(
                    *[
                        str(raw.get(key, "-"))
                        for key in (
                            "ticket",
                            "symbol",
                            "signal",
                            "order_type",
                            "volume",
                            "price",
                            "stop_loss",
                            "take_profit",
                            "expiration",
                        )
                    ]
                )
    else:
        pending_table.add_row("-", "-", "-", "-", "-", "-", "-", "-", "No pending orders")
    position_table = Table(title="Open Positions", expand=True)
    for heading in ("Ticket", "Symbol", "Side", "Volume", "Open", "Current", "Profit"):
        position_table.add_column(heading, no_wrap=True)

    positions = _items(payload.get("positions"))
    if positions:
        for raw in positions:
            if not isinstance(raw, dict):
                continue
            position: dict[str, Any] = raw
            profit = _number(position.get("profit"))
            position_table.add_row(
                str(position.get("ticket", "-")),
                str(position.get("symbol", "-")),
                str(position.get("signal", "-")),
                str(position.get("volume", "-")),
                str(position.get("price_open", "-")),
                str(position.get("price_current", "-")),
                Text(f"{profit:,.2f}", style="green" if profit >= 0 else "red"),
            )
    else:
        position_table.add_row("-", "-", "-", "-", "-", "-", "No open positions")

    opened = _items(payload.get("opened"))
    closed = _items(payload.get("closed"))
    opened_text = ", ".join(str(item) for item in opened) if opened else "None"
    closed_text = ", ".join(str(item) for item in closed) if closed else "None"
    stop_text = "YES" if payload.get("stop_requested") else "NO"

    events = Table.grid(expand=True)
    events.add_column()
    events.add_column()
    events.add_column()
    events.add_row(
        Text.from_markup(f"[bold green]Opened[/bold green]: {opened_text}"),
        Text.from_markup(f"[bold cyan]Closed[/bold cyan]: {closed_text}"),
        Text.from_markup(f"[bold]Stop requested[/bold]: {stop_text}"),
    )

    border_style = "cyan" if "Demo" in title else "magenta"
    return Group(
        Panel(summary, title=title, border_style=border_style),
        prediction_table,
        pending_table,
        position_table,
        Panel(events, title="Latest Cycle", border_style="blue"),
        Text(
            "Press Ctrl+C to stop the dashboard, or run the stop command elsewhere.",
            style="dim",
        ),
    )

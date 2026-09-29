"""Rich rendering for explainable strategy decisions."""

from rich.panel import Panel
from rich.table import Table

from grandmaster_fx.console import console
from grandmaster_fx.strategies.models import Signal, StrategyDecision


def _number(value: float | None, digits: int = 8) -> str:
    return "N/A" if value is None else f"{value:.{digits}g}"


def render_strategy_decision(decision: StrategyDecision, timeframe: str) -> None:
    """Render a strategy decision and its complete numerical context."""
    color = {Signal.BUY: "green", Signal.SELL: "red", Signal.HOLD: "yellow"}[decision.signal]
    console.print(
        Panel.fit(
            f"{decision.symbol} | {timeframe} | {decision.signal.value}",
            style=color,
        )
    )
    table = Table(show_header=False)
    table.add_column("Field", style="bold")
    table.add_column("Value", justify="right")
    rows = (
        ("Timestamp", decision.timestamp.isoformat()),
        ("Reason", ", ".join(reason.value for reason in decision.reasons)),
        ("Entry proposal", _number(decision.entry)),
        ("Stop proposal", _number(decision.stop_loss)),
        ("Target proposal", _number(decision.take_profit)),
        ("Reward/risk", _number(decision.reward_risk, 4)),
        ("Fast EMA", _number(decision.fast_ema)),
        ("Slow EMA", _number(decision.slow_ema)),
        ("RSI", _number(decision.rsi, 6)),
        ("ATR", _number(decision.atr)),
        ("ROC (%)", _number(decision.roc, 6)),
        ("Spread points", str(decision.spread_points)),
    )
    for row in rows:
        table.add_row(*row)
    console.print(table)
    console.print("[dim]Decision only. No order was constructed or submitted.[/dim]")

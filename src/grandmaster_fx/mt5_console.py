"""Rich rendering for MetaTrader 5 diagnostics."""

from rich.panel import Panel
from rich.table import Table

from grandmaster_fx.application.mt5_diagnostics import Mt5DiagnosticReport
from grandmaster_fx.console import console
from grandmaster_fx.domain.mt5 import AccountSnapshot, TerminalSnapshot


def _yes_no(*, value: bool) -> str:
    return "[green]Yes[/green]" if value else "[yellow]No[/yellow]"


def render_terminal(terminal: TerminalSnapshot) -> None:
    """Render a terminal snapshot."""
    table = Table(title="MetaTrader 5 terminal", show_header=False)
    table.add_column("Property", style="bold")
    table.add_column("Value")
    table.add_row("Connected", _yes_no(value=terminal.connected))
    table.add_row("Build", str(terminal.build))
    table.add_row("Name", terminal.name)
    table.add_row("Company", terminal.company)
    table.add_row("Trading allowed", _yes_no(value=terminal.trade_allowed))
    table.add_row("Python API enabled", _yes_no(value=not terminal.trade_api_disabled))
    table.add_row("Terminal path", terminal.path)
    console.print(table)


def render_account(account: AccountSnapshot) -> None:
    """Render a sanitized demo-account snapshot."""
    table = Table(title="MT5 demo account", show_header=False)
    table.add_column("Property", style="bold")
    table.add_column("Value", justify="right")
    table.add_row("Login", str(account.login))
    table.add_row("Mode", account.trade_mode.name)
    table.add_row("Server", account.server)
    table.add_row("Company", account.company)
    table.add_row("Currency", account.currency)
    table.add_row("Leverage", f"1:{account.leverage}")
    table.add_row("Balance", f"{account.balance:,.2f}")
    table.add_row("Equity", f"{account.equity:,.2f}")
    table.add_row("Floating P/L", f"{account.profit:,.2f}")
    table.add_row("Margin", f"{account.margin:,.2f}")
    table.add_row("Free margin", f"{account.margin_free:,.2f}")
    table.add_row("Manual trading", _yes_no(value=account.trade_allowed))
    table.add_row("Algorithmic trading", _yes_no(value=account.trade_expert))
    console.print(table)


def render_report(report: Mt5DiagnosticReport) -> None:
    """Render a complete connection report."""
    version = ".".join(str(part) for part in report.package_version)
    console.print(Panel.fit(f"MT5 connection healthy | version {version}", style="green"))
    render_terminal(report.terminal)
    render_account(report.account)

"""Shared Rich console and display helpers."""

from dataclasses import dataclass

from rich.console import Console
from rich.table import Table

console = Console()


@dataclass(frozen=True, slots=True)
class CheckResult:
    """One diagnostic check rendered by the doctor command."""

    name: str
    ok: bool
    detail: str


def render_checks(results: list[CheckResult]) -> None:
    """Render diagnostic results as a compact Rich table."""
    table = Table(title="Grandmaster FX health check", show_lines=False)
    table.add_column("Check", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Details")

    for result in results:
        status = "[green]PASS[/green]" if result.ok else "[red]FAIL[/red]"
        table.add_row(result.name, status, result.detail)

    console.print(table)

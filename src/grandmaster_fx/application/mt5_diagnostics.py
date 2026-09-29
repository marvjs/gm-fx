"""Read-only MT5 diagnostic orchestration."""

from dataclasses import dataclass

from grandmaster_fx.domain.mt5 import AccountSnapshot, TerminalSnapshot
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway


@dataclass(frozen=True, slots=True)
class Mt5DiagnosticReport:
    """Combined terminal and demo-account connection report."""

    package_version: tuple[int, int, str]
    terminal: TerminalSnapshot
    account: AccountSnapshot


def inspect_connection(gateway: Mt5Gateway) -> Mt5DiagnosticReport:
    """Collect all read-only MT5 diagnostics from an active gateway."""
    return Mt5DiagnosticReport(
        package_version=gateway.version(),
        terminal=gateway.terminal(),
        account=gateway.account(),
    )

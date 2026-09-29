"""MT5 Rich rendering tests."""

from grandmaster_fx.application.mt5_diagnostics import Mt5DiagnosticReport
from grandmaster_fx.console import console
from grandmaster_fx.domain.mt5 import AccountSnapshot, TerminalSnapshot
from grandmaster_fx.mt5_console import render_account, render_report, render_terminal

ACCOUNT = AccountSnapshot.from_mapping(
    {
        "login": 123,
        "trade_mode": 0,
        "server": "Broker-Demo",
        "company": "Broker",
        "currency": "USD",
        "leverage": 200,
        "balance": 1000,
        "equity": 990,
        "margin": 10,
        "margin_free": 980,
        "profit": -10,
        "trade_allowed": True,
        "trade_expert": False,
    }
)
TERMINAL = TerminalSnapshot.from_mapping(
    {
        "connected": True,
        "trade_allowed": True,
        "tradeapi_disabled": False,
        "build": 5000,
        "name": "MT5",
        "company": "MetaQuotes",
        "path": "C:/MT5",
    }
)


def test_render_terminal() -> None:
    with console.capture() as capture:
        render_terminal(TERMINAL)
    assert "MetaTrader 5 terminal" in capture.get()
    assert "Python API enabled" in capture.get()


def test_render_account() -> None:
    with console.capture() as capture:
        render_account(ACCOUNT)
    assert "MT5 demo account" in capture.get()
    assert "Broker-Demo" in capture.get()


def test_render_complete_report() -> None:
    report = Mt5DiagnosticReport((5, 0, "6231"), TERMINAL, ACCOUNT)
    with console.capture() as capture:
        render_report(report)
    assert "MT5 connection healthy" in capture.get()

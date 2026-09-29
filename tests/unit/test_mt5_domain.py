"""MT5 domain safety tests."""

import pytest

from grandmaster_fx.domain.mt5 import AccountSnapshot, AccountTradeMode, TerminalSnapshot
from grandmaster_fx.exceptions import Mt5DataError, SafetyViolationError

ACCOUNT = {
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
    "trade_expert": True,
}
TERMINAL = {
    "connected": True,
    "trade_allowed": True,
    "tradeapi_disabled": False,
    "build": 5000,
    "name": "MetaTrader 5",
    "company": "MetaQuotes",
    "path": "C:/MT5",
}


def test_demo_account_is_accepted() -> None:
    account = AccountSnapshot.from_mapping(ACCOUNT)
    assert account.trade_mode is AccountTradeMode.DEMO


def test_real_account_is_rejected() -> None:
    with pytest.raises(SafetyViolationError, match="not a demo"):
        AccountSnapshot.from_mapping({**ACCOUNT, "trade_mode": 2})


def test_incomplete_account_is_rejected() -> None:
    with pytest.raises(Mt5DataError, match="incomplete account"):
        AccountSnapshot.from_mapping({})


def test_terminal_snapshot_is_parsed() -> None:
    terminal = TerminalSnapshot.from_mapping(TERMINAL)
    assert terminal.connected
    assert not terminal.trade_api_disabled


def test_incomplete_terminal_is_rejected() -> None:
    with pytest.raises(Mt5DataError, match="incomplete terminal"):
        TerminalSnapshot.from_mapping({})

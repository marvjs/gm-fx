"""Broker-neutral snapshots derived from MetaTrader 5 named tuples."""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import IntEnum
from typing import Any

from grandmaster_fx.exceptions import Mt5DataError, SafetyViolationError


class AccountTradeMode(IntEnum):
    """MetaTrader account trade modes."""

    DEMO = 0
    CONTEST = 1
    REAL = 2


@dataclass(frozen=True, slots=True)
class TerminalSnapshot:
    """Safe subset of terminal state used for diagnostics."""

    connected: bool
    trade_allowed: bool
    trade_api_disabled: bool
    build: int
    name: str
    company: str
    path: str

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "TerminalSnapshot":
        """Build a snapshot from MT5 terminal information."""
        try:
            return cls(
                connected=bool(values["connected"]),
                trade_allowed=bool(values["trade_allowed"]),
                trade_api_disabled=bool(values.get("tradeapi_disabled", False)),
                build=int(values["build"]),
                name=str(values["name"]),
                company=str(values["company"]),
                path=str(values["path"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            message = f"MT5 returned incomplete terminal information: {error}"
            raise Mt5DataError(message) from error


@dataclass(frozen=True, slots=True)
class AccountSnapshot:
    """Safe account summary with no password or private credentials."""

    login: int
    trade_mode: AccountTradeMode
    server: str
    company: str
    currency: str
    leverage: int
    balance: float
    equity: float
    margin: float
    margin_free: float
    profit: float
    trade_allowed: bool
    trade_expert: bool

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "AccountSnapshot":
        """Build and validate an account snapshot from MT5 account information."""
        try:
            trade_mode = AccountTradeMode(int(values["trade_mode"]))
            snapshot = cls(
                login=int(values["login"]),
                trade_mode=trade_mode,
                server=str(values["server"]),
                company=str(values["company"]),
                currency=str(values["currency"]),
                leverage=int(values["leverage"]),
                balance=float(values["balance"]),
                equity=float(values["equity"]),
                margin=float(values["margin"]),
                margin_free=float(values["margin_free"]),
                profit=float(values["profit"]),
                trade_allowed=bool(values["trade_allowed"]),
                trade_expert=bool(values["trade_expert"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            message = f"MT5 returned incomplete account information: {error}"
            raise Mt5DataError(message) from error
        return snapshot

    def require_demo(self) -> None:
        """Explicitly reject every non-demo account (used by demo CLI checks)."""
        if self.trade_mode is not AccountTradeMode.DEMO:
            message = (
                f"Account {self.login} is not a demo account. "
                "The requested operation is strictly limited to DEMO accounts."
            )
            raise SafetyViolationError(message)

    def require_real(self) -> None:
        """Reject demo and contest accounts for live commands."""
        if self.trade_mode is not AccountTradeMode.REAL:
            message = (
                f"Account {self.login} is not a real account. "
                "The requested operation is strictly limited to REAL accounts."
            )
            raise SafetyViolationError(message)

    def verify_execution_safety(self, allow_live_account: bool) -> None:  # noqa: FBT001
        """Reject real accounts unless explicitly authorized in the application config."""
        if self.trade_mode is not AccountTradeMode.DEMO and not allow_live_account:
            message = (
                f"Account {self.login} is a real/contest account. "
                "Grandmaster FX requires 'allow_live_account = true' in app.toml for live trading."
            )
            raise SafetyViolationError(message)

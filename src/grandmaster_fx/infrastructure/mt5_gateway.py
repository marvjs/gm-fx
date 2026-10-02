"""Thin, read-only adapter around the official MetaTrader 5 Python package."""

from __future__ import annotations

from datetime import datetime
from importlib import import_module
from types import ModuleType
from typing import Any, Self, cast

from grandmaster_fx.config import Mt5Secrets
from grandmaster_fx.domain.market_data import Bar, Tick, Timeframe
from grandmaster_fx.domain.mt5 import AccountSnapshot, TerminalSnapshot
from grandmaster_fx.domain.symbols import SymbolSnapshot
from grandmaster_fx.exceptions import (
    Mt5ConnectionError,
    Mt5DataError,
    Mt5PackageUnavailableError,
)
from grandmaster_fx.execution.models import (
    ExecutionCandidate,
    PendingOrderSnapshot,
    PositionSnapshot,
)
from grandmaster_fx.pending.models import PendingOrderPlan, PendingOrderType
from grandmaster_fx.strategies.models import Signal


def _structured_row_mapping(value: Any) -> dict[str, Any]:
    """Convert an MT5 named tuple or NumPy structured scalar to a plain mapping."""
    if hasattr(value, "_asdict"):
        return dict(value._asdict())

    dtype = getattr(value, "dtype", None)
    names = getattr(dtype, "names", None)
    if names:
        return {
            name: value[name].item() if hasattr(value[name], "item") else value[name]
            for name in names
        }

    message = f"Unsupported MT5 bar row type: {type(value).__name__}"
    raise Mt5DataError(message)


class Mt5Gateway:
    """Own the MT5 connection lifecycle and expose read-only snapshots."""

    def __init__(self, secrets: Mt5Secrets, module: Any | None = None) -> None:
        self._secrets = secrets
        self._module = module
        self._connected = False

    def __enter__(self) -> Self:
        self.connect()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    def _load_module(self) -> ModuleType:
        if self._module is not None:
            return cast("ModuleType", self._module)
        try:
            self._module = import_module("MetaTrader5")
        except ImportError as error:
            message = (
                "The official MetaTrader5 package is unavailable. "
                "Run `uv sync --locked` on Windows."
            )
            raise Mt5PackageUnavailableError(message) from error
        return self._module

    def _last_error(self) -> str:
        module = self._load_module()
        code, description = module.last_error()
        return f"MT5 error {code}: {description}"

    def connect(self) -> None:
        """Initialize the terminal and optionally authenticate explicitly."""
        if self._connected:
            return
        module = self._load_module()
        kwargs: dict[str, object] = {"timeout": self._secrets.mt5_timeout_ms}
        if self._secrets.mt5_terminal_path is not None:
            kwargs["path"] = str(self._secrets.mt5_terminal_path)
        if not module.initialize(**kwargs):
            message = f"Could not initialize MetaTrader 5. {self._last_error()}"
            raise Mt5ConnectionError(message)
        self._connected = True
        if self._secrets.has_credentials and not module.login(
            self._secrets.mt5_login,
            password=self._secrets.mt5_password,
            server=self._secrets.mt5_server,
            timeout=self._secrets.mt5_timeout_ms,
        ):
            error = self._last_error()
            self.close()
            message = f"Could not authenticate the MT5 account. {error}"
            raise Mt5ConnectionError(message)

    def close(self) -> None:
        """Shut down an initialized MT5 connection safely."""
        if self._connected:
            self._load_module().shutdown()
            self._connected = False

    def version(self) -> tuple[int, int, str]:
        """Return the connected terminal version tuple."""
        value = self._load_module().version()
        if value is None:
            message = f"Could not retrieve MT5 version. {self._last_error()}"
            raise Mt5DataError(message)
        return int(value[0]), int(value[1]), str(value[2])

    def terminal(self) -> TerminalSnapshot:
        """Return validated terminal information."""
        value = self._load_module().terminal_info()
        if value is None:
            message = f"Could not retrieve terminal information. {self._last_error()}"
            raise Mt5DataError(message)
        return TerminalSnapshot.from_mapping(value._asdict())

    def account(self) -> AccountSnapshot:
        """Return a validated account snapshot."""
        value = self._load_module().account_info()
        if value is None:
            message = f"Could not retrieve account information. {self._last_error()}"
            raise Mt5DataError(message)
        return AccountSnapshot.from_mapping(value._asdict())

    def symbols(self, allowed: frozenset[str]) -> list[SymbolSnapshot]:
        """Return currency-only broker symbols."""
        from grandmaster_fx.domain.symbols import SymbolSnapshot

        values = self._load_module().symbols_get()
        if values is None:
            raise Mt5DataError(f"Could not retrieve symbols. {self._last_error()}")
        snapshots = [SymbolSnapshot.from_mapping(value._asdict(), allowed) for value in values]
        return [item for item in snapshots if item is not None]

    def select_symbol(self, name: str) -> None:
        """Make a symbol available in Market Watch."""
        if not self._load_module().symbol_select(name, True):
            raise Mt5DataError(f"Could not select symbol {name}. {self._last_error()}")

    def symbol(self, name: str, allowed: frozenset[str]) -> SymbolSnapshot:
        """Retrieve one currency symbol by its exact broker name."""
        from grandmaster_fx.domain.symbols import SymbolSnapshot

        value = self._load_module().symbol_info(name)
        if value is None:
            raise Mt5DataError(f"Could not retrieve symbol {name}. {self._last_error()}")
        snapshot = SymbolSnapshot.from_mapping(value._asdict(), allowed)
        if snapshot is None:
            raise Mt5DataError(f"Symbol {name} is not an allowed currency pair")
        return snapshot

    def tick(self, name: str) -> Tick:
        """Return the latest validated tick."""
        value = self._load_module().symbol_info_tick(name)
        if value is None:
            raise Mt5DataError(f"Could not retrieve tick for {name}. {self._last_error()}")
        return Tick.from_mapping(value._asdict())

    def bars(self, name: str, timeframe: Timeframe, count: int, start: int = 1) -> list[Bar]:
        """Return validated bars, defaulting to completed candles only."""
        module = self._load_module()
        constant = getattr(module, f"TIMEFRAME_{timeframe.value}")
        values = module.copy_rates_from_pos(name, constant, start, count)
        if values is None:
            raise Mt5DataError(f"Could not retrieve bars for {name}. {self._last_error()}")
        return [Bar.from_mapping(_structured_row_mapping(value)) for value in values]

    def positions(self, magic: int) -> list[PositionSnapshot]:
        """Return positions owned by this engine."""
        values = self._load_module().positions_get()
        if values is None:
            raise Mt5DataError(f"Could not retrieve positions. {self._last_error()}")
        return [
            PositionSnapshot.from_mapping(value._asdict())
            for value in values
            if int(value.magic) == magic
        ]

    def pending_orders(self, magic: int) -> list[PendingOrderSnapshot]:
        values = self._load_module().orders_get()
        if values is None:
            raise Mt5DataError(f"Could not retrieve pending orders. {self._last_error()}")
        return [
            PendingOrderSnapshot.from_mapping(item._asdict())
            for item in values
            if int(item.magic) == magic
        ]

    def open_pending_order(  # noqa: PLR0913
        self,
        plan: PendingOrderPlan,
        volume: float,
        magic: int,
        comment: str,
        deviation: int,
        expiration: datetime,
        dry_run: bool,  # noqa: FBT001
    ) -> int | None:
        module = self._load_module()
        kinds = {
            PendingOrderType.BUY_STOP: module.ORDER_TYPE_BUY_STOP,
            PendingOrderType.SELL_STOP: module.ORDER_TYPE_SELL_STOP,
            PendingOrderType.BUY_LIMIT: module.ORDER_TYPE_BUY_LIMIT,
            PendingOrderType.SELL_LIMIT: module.ORDER_TYPE_SELL_LIMIT,
        }
        request = {
            "action": module.TRADE_ACTION_PENDING,
            "symbol": plan.symbol,
            "volume": volume,
            "type": kinds[plan.order_type],
            "price": plan.trigger_price,
            "sl": plan.stop_loss,
            "tp": plan.take_profit,
            "deviation": deviation,
            "magic": magic,
            "comment": comment,
            "type_time": module.ORDER_TIME_SPECIFIED,
            "expiration": int(expiration.timestamp()),
            "type_filling": module.ORDER_FILLING_RETURN,
        }
        checked = module.order_check(request)
        if checked is None or int(checked.retcode) != 0:
            raise Mt5DataError(f"Pending order check failed. {self._last_error()}")
        if dry_run:
            return None
        result = module.order_send(request)
        if result is None or int(result.retcode) != int(module.TRADE_RETCODE_DONE):
            raise Mt5DataError(f"Pending order rejected. {self._last_error()}")
        return int(result.order)

    def cancel_pending_order(self, ticket: int, magic: int, dry_run: bool) -> bool:  # noqa: FBT001
        if not any(item.ticket == ticket for item in self.pending_orders(magic)):
            return False
        if dry_run:
            return True
        module = self._load_module()
        result = module.order_send({"action": module.TRADE_ACTION_REMOVE, "order": ticket})
        return result is not None and int(result.retcode) == int(module.TRADE_RETCODE_DONE)

    def history_orders(
        self,
        start: datetime,
        end: datetime,
        magic: int,
    ) -> list[dict[str, Any]]:
        """Return profile-owned broker order-history rows as plain mappings."""
        values = self._load_module().history_orders_get(start, end)
        if values is None:
            raise Mt5DataError(f"Could not retrieve order history. {self._last_error()}")
        return [item._asdict() for item in values if int(item.magic) == magic]

    def history_deals(
        self,
        start: datetime,
        end: datetime,
        magic: int,
    ) -> list[dict[str, Any]]:
        """Return profile-owned broker deal-history rows as plain mappings."""
        values = self._load_module().history_deals_get(start, end)
        if values is None:
            raise Mt5DataError(f"Could not retrieve deal history. {self._last_error()}")
        return [item._asdict() for item in values if int(item.magic) == magic]

    def open_order(
        self,
        candidate: ExecutionCandidate,
        volume: float,
        magic: int,
        comment: str,
        deviation: int,
        dry_run: bool,  # noqa: FBT001
    ) -> int | None:
        """Check and optionally submit one market order with precise error extraction."""
        module = self._load_module()
        tick = self.tick(candidate.symbol)
        is_buy = candidate.signal is Signal.BUY
        request = {
            "action": module.TRADE_ACTION_DEAL,
            "symbol": candidate.symbol,
            "volume": volume,
            "type": module.ORDER_TYPE_BUY if is_buy else module.ORDER_TYPE_SELL,
            "price": tick.ask if is_buy else tick.bid,
            "sl": candidate.stop_loss,
            "tp": candidate.take_profit,
            "deviation": deviation,
            "magic": magic,
            "comment": comment,
            "type_time": module.ORDER_TIME_GTC,
            "type_filling": module.ORDER_FILLING_IOC,
        }
        checked = module.order_check(request)
        if checked is None or int(checked.retcode) != 0:
            raise Mt5DataError(f"Order check failed. {self._last_error()}")
        if dry_run:
            return None
        result = module.order_send(request)
        if result is None:
            raise Mt5DataError(f"Order send crashed internally. {self._last_error()}")
        if int(result.retcode) != int(module.TRADE_RETCODE_DONE):
            raise Mt5DataError(
                f"Order rejected by broker. Code: {result.retcode}, Reason: {result.comment}"
            )
        return int(result.order or result.deal)

    def close_position(
        self,
        position: PositionSnapshot,
        magic: int,
        comment: str,
        deviation: int,
        dry_run: bool,  # noqa: FBT001
    ) -> bool:
        """Close one engine-owned position with precise error extraction."""
        if position.magic != magic:
            message = "Refusing to close a position owned by another engine"
            raise Mt5DataError(message)
        module = self._load_module()
        tick = self.tick(position.symbol)
        is_buy = position.signal is Signal.BUY
        request = {
            "action": module.TRADE_ACTION_DEAL,
            "position": position.ticket,
            "symbol": position.symbol,
            "volume": position.volume,
            "type": module.ORDER_TYPE_SELL if is_buy else module.ORDER_TYPE_BUY,
            "price": tick.bid if is_buy else tick.ask,
            "deviation": deviation,
            "magic": magic,
            "comment": comment,
            "type_time": module.ORDER_TIME_GTC,
            "type_filling": module.ORDER_FILLING_IOC,
        }
        checked = module.order_check(request)
        if checked is None or int(checked.retcode) != 0:
            raise Mt5DataError(f"Close check failed. {self._last_error()}")
        if dry_run:
            return True
        result = module.order_send(request)
        if result is None:
            raise Mt5DataError(f"Close send crashed internally. {self._last_error()}")
        if int(result.retcode) != int(module.TRADE_RETCODE_DONE):
            raise Mt5DataError(
                f"Close rejected by broker. Code: {result.retcode}, Reason: {result.comment}"
            )
        return True

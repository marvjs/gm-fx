"""Read-only and execution MT5 gateway tests."""

from collections.abc import Callable
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from grandmaster_fx.config import Mt5Secrets
from grandmaster_fx.exceptions import Mt5ConnectionError, Mt5DataError
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway


def nt(**values: object) -> object:
    return SimpleNamespace(**values, _asdict=lambda: values)


def module() -> Mock:
    api = Mock()
    api.initialize.return_value = True
    api.login.return_value = True
    api.last_error.return_value = (-1, "failure")
    api.version.return_value = (5, 0, "6231")
    api.terminal_info.return_value = nt(
        connected=True,
        trade_allowed=True,
        tradeapi_disabled=False,
        build=5000,
        name="MT5",
        company="MetaQuotes",
        path="C:/MT5",
    )
    api.account_info.return_value = nt(
        login=123,
        trade_mode=0,
        server="Broker-Demo",
        company="Broker",
        currency="USD",
        leverage=200,
        balance=1000,
        equity=1000,
        margin=0,
        margin_free=1000,
        profit=0,
        trade_allowed=True,
        trade_expert=True,
    )
    return api


def test_context_manager_initializes_and_shuts_down() -> None:
    api = module()
    with Mt5Gateway(Mt5Secrets(_env_file=None), api) as gateway:
        assert gateway.account().login == 123
    api.initialize.assert_called_once()
    api.shutdown.assert_called_once()


def test_explicit_credentials_trigger_login() -> None:
    api = module()
    secrets = Mt5Secrets(
        mt5_login=123, mt5_password="secret", mt5_server="Broker-Demo", _env_file=None
    )
    with Mt5Gateway(secrets, api):
        pass
    api.login.assert_called_once()


def test_initialize_failure_reports_last_error() -> None:
    api = module()
    api.initialize.return_value = False
    with pytest.raises(Mt5ConnectionError, match="MT5 error -1"):
        Mt5Gateway(Mt5Secrets(_env_file=None), api).connect()


def test_login_failure_closes_connection() -> None:
    api = module()
    api.login.return_value = False
    secrets = Mt5Secrets(
        mt5_login=123, mt5_password="secret", mt5_server="Broker-Demo", _env_file=None
    )
    with pytest.raises(Mt5ConnectionError, match="authenticate"):
        Mt5Gateway(secrets, api).connect()
    api.shutdown.assert_called_once()


def test_missing_terminal_data_is_reported() -> None:
    api = module()
    api.terminal_info.return_value = None
    gateway = Mt5Gateway(Mt5Secrets(_env_file=None), api)
    with pytest.raises(Mt5DataError, match="terminal information"):
        gateway.terminal()


def test_missing_version_is_reported() -> None:
    api = module()
    api.version.return_value = None
    gateway = Mt5Gateway(Mt5Secrets(_env_file=None), api)
    with pytest.raises(Mt5DataError, match="version"):
        gateway.version()


def test_gateway_returns_version_terminal_and_account() -> None:
    api = module()
    gateway = Mt5Gateway(Mt5Secrets(_env_file=None), api)
    assert gateway.version() == (5, 0, "6231")
    assert gateway.terminal().build == 5000
    assert gateway.account().login == 123


def test_connect_is_idempotent_and_passes_terminal_path() -> None:
    api = module()
    secrets = Mt5Secrets(mt5_terminal_path="C:/MT5/terminal64.exe", _env_file=None)
    gateway = Mt5Gateway(secrets, api)
    gateway.connect()
    gateway.connect()
    gateway.close()
    api.initialize.assert_called_once_with(path=str(secrets.mt5_terminal_path), timeout=60_000)


def test_missing_account_data_is_reported() -> None:
    api = module()
    api.account_info.return_value = None
    gateway = Mt5Gateway(Mt5Secrets(_env_file=None), api)
    with pytest.raises(Mt5DataError, match="account information"):
        gateway.account()


def symbol_info(**updates: object) -> object:
    values: dict[str, object] = {
        "name": "EURUSDm",
        "currency_base": "EUR",
        "currency_profit": "USD",
        "description": "Euro vs US Dollar",
        "select": True,
        "visible": True,
        "trade_mode": 4,
        "digits": 5,
        "point": 0.00001,
        "spread": 8,
        "spread_float": True,
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "trade_contract_size": 100000.0,
        "volume_min": 0.01,
        "volume_max": 200.0,
        "volume_step": 0.01,
        "volume_limit": 0.0,
        "trade_stops_level": 0,
        "trade_freeze_level": 0,
    }
    values.update(updates)
    return nt(**values)


def test_symbols_filters_non_forex_and_selects_symbol() -> None:
    api = module()
    api.symbols_get.return_value = (
        symbol_info(),
        symbol_info(name="XAUUSDm", currency_base="XAU", currency_profit="USD"),
    )
    api.symbol_select.return_value = True
    gateway = Mt5Gateway(Mt5Secrets(_env_file=None), api)

    symbols = gateway.symbols(frozenset({"EUR", "USD"}))
    gateway.select_symbol("EURUSDm")

    assert [item.name for item in symbols] == ["EURUSDm"]
    api.symbol_select.assert_called_once_with("EURUSDm", True)


def test_symbol_tick_and_bars_are_parsed() -> None:
    from grandmaster_fx.domain.market_data import Timeframe

    api = module()
    api.symbol_info.return_value = symbol_info()
    api.symbol_info_tick.return_value = nt(
        time_msc=1_000,
        bid=1.1,
        ask=1.2,
        last=1.15,
        volume_real=2.0,
    )
    api.TIMEFRAME_M1 = 1
    api.copy_rates_from_pos.return_value = [
        nt(
            time=60,
            open=1.0,
            high=1.2,
            low=0.9,
            close=1.1,
            tick_volume=10,
            spread=5,
            real_volume=0,
        )
    ]
    gateway = Mt5Gateway(Mt5Secrets(_env_file=None), api)

    assert gateway.symbol("EURUSDm", frozenset({"EUR", "USD"})).name == "EURUSDm"
    assert gateway.tick("EURUSDm").spread == pytest.approx(0.1)
    assert len(gateway.bars("EURUSDm", Timeframe.M1, 1)) == 1
    api.copy_rates_from_pos.assert_called_once_with("EURUSDm", 1, 1, 1)


def test_order_send_rejection_is_parsed_accurately() -> None:
    from grandmaster_fx.execution.models import ExecutionCandidate
    from grandmaster_fx.strategies.models import Signal

    api = module()
    api.symbol_info_tick.return_value = nt(
        time_msc=1_000, bid=1.1, ask=1.2, last=1.15, volume_real=2.0
    )

    # Simulate a broker rejection due to invalid volume
    api.order_check.return_value = nt(retcode=0)
    api.TRADE_RETCODE_DONE = 10009
    api.order_send.return_value = nt(retcode=10014, comment="Invalid volume")

    gateway = Mt5Gateway(Mt5Secrets(_env_file=None), api)
    candidate = ExecutionCandidate("EURUSDm", Signal.BUY, 0.8, 1.2, 0.9, 1.5)

    with pytest.raises(Mt5DataError, match="rejected by broker"):
        gateway.open_order(candidate, 0.01, 123, "test", 10, dry_run=False)


@pytest.mark.parametrize(
    ("method", "setup", "message"),
    [
        ("symbols", lambda api: setattr(api, "symbols_get", Mock(return_value=None)), "symbols"),
        ("select", lambda api: setattr(api, "symbol_select", Mock(return_value=False)), "select"),
        (
            "symbol",
            lambda api: setattr(api, "symbol_info", Mock(return_value=None)),
            "retrieve symbol",
        ),
        (
            "tick",
            lambda api: setattr(api, "symbol_info_tick", Mock(return_value=None)),
            "retrieve tick",
        ),
        (
            "bars",
            lambda api: setattr(api, "copy_rates_from_pos", Mock(return_value=None)),
            "retrieve bars",
        ),
    ],
)
def test_market_data_gateway_errors(
    method: str, setup: Callable[[Mock], None], message: str
) -> None:
    from grandmaster_fx.domain.market_data import Timeframe

    api = module()
    api.TIMEFRAME_M1 = 1
    setup(api)
    gateway = Mt5Gateway(Mt5Secrets(_env_file=None), api)
    allowed = frozenset({"EUR", "USD"})

    with pytest.raises(Mt5DataError, match=message):
        if method == "symbols":
            gateway.symbols(allowed)
        elif method == "select":
            gateway.select_symbol("EURUSDm")
        elif method == "symbol":
            gateway.symbol("EURUSDm", allowed)
        elif method == "tick":
            gateway.tick("EURUSDm")
        else:
            gateway.bars("EURUSDm", Timeframe.M1, 1)

"""Dynamic risk engine tests."""

import pytest

from grandmaster_fx.config.risk import RiskParameters, RiskSettings
from grandmaster_fx.domain.mt5 import AccountSnapshot
from grandmaster_fx.domain.symbols import ForexIdentity, SymbolSnapshot
from grandmaster_fx.execution.models import CloseReason
from grandmaster_fx.execution.risk import RiskManager


def account(equity: float, balance: float = 1000.0) -> AccountSnapshot:
    return AccountSnapshot.from_mapping(
        {
            "login": 1,
            "trade_mode": 0,
            "server": "Demo",
            "company": "Broker",
            "currency": "USD",
            "leverage": 100,
            "balance": balance,
            "equity": equity,
            "margin": 0,
            "margin_free": equity,
            "profit": equity - balance,
            "trade_allowed": True,
            "trade_expert": True,
        }
    )


def symbol() -> SymbolSnapshot:
    return SymbolSnapshot(
        name="EURUSDm",
        identity=ForexIdentity("EURUSD", "EUR", "USD"),
        description="",
        selected=True,
        visible=True,
        trade_mode=4,
        digits=5,
        point=0.00001,
        spread_points=5,
        spread_float=True,
        tick_size=0.00001,
        tick_value=1.0,
        contract_size=100000.0,
        volume_min=0.01,
        volume_max=100.0,
        volume_step=0.01,
        volume_limit=0.0,
        stops_level=0,
        freeze_level=0,
    )


def test_circuit_breakers() -> None:
    settings = RiskSettings(
        risk=RiskParameters(
            risk_per_trade_percent=1.0,
            maximum_daily_loss_percent=5.0,
            maximum_floating_loss_percent=3.0,
            maximum_open_positions=3,
        )
    )
    manager = RiskManager(settings)

    # Safe
    assert manager.check_circuit_breakers(account(1000.0), 1000.0, 0.0) is None

    # Daily loss (5%) -> $50
    assert (
        manager.check_circuit_breakers(account(950.0), 1000.0, -50.0) is CloseReason.EMERGENCY_STOP
    )

    # Floating loss (3%) -> $30 on 1000 balance
    assert (
        manager.check_circuit_breakers(account(970.0), 1000.0, -30.0)
        is CloseReason.FLOATING_LOSS_LIMIT
    )


def test_calculate_volume() -> None:
    settings = RiskSettings(
        risk=RiskParameters(
            risk_per_trade_percent=1.0,
            maximum_daily_loss_percent=5.0,
            maximum_floating_loss_percent=3.0,
            maximum_open_positions=3,
        )
    )
    manager = RiskManager(settings)

    # Risk 1% of $1000 = $10.00.
    # Entry 1.10000, Stop 1.09000 -> 1000 ticks. 1 tick = $1.00. Loss for 1 lot = $1000.
    # Required volume = $10 / $1000 = 0.01 lots.
    vol = manager.calculate_volume(1000.0, 1.10000, 1.09000, symbol())
    assert vol == 0.01

    with pytest.raises(ValueError, match="positive"):
        manager.calculate_volume(1000.0, 1.1, 1.1, symbol())

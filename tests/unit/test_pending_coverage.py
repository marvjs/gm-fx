"""Focused branch coverage for pending-order models and configuration."""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from grandmaster_fx.config.pending_orders import load_pending_order_settings
from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.pending.models import PendingOrderPlan, PendingOrderType
from grandmaster_fx.strategies.models import Signal


def plan(**changes: object) -> PendingOrderPlan:
    values: dict[str, object] = {
        "identity": "identity",
        "strategy_id": "momentum_continuation",
        "symbol": "USDJPYm",
        "timeframe": Timeframe.M5,
        "signal": Signal.BUY,
        "order_type": PendingOrderType.BUY_STOP,
        "source_time": datetime(2026, 1, 1, tzinfo=UTC),
        "trigger_price": 100.0,
        "stop_loss": 99.0,
        "take_profit": 102.0,
        "maximum_wait_bars": 3,
        "score": 0.8,
    }
    values.update(changes)
    return PendingOrderPlan(**values)  # type: ignore[arg-type]


def test_pending_configuration_loads_default_file() -> None:
    settings = load_pending_order_settings()
    assert settings.pending.enabled
    assert settings.pending.maximum_wait_bars == 3


def test_pending_configuration_wraps_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing-pending-orders.toml"
    with pytest.raises(ConfigurationError, match="Pending-order configuration is invalid"):
        load_pending_order_settings(missing)


def test_pending_plan_rejects_hold_signal() -> None:
    with pytest.raises(ValueError, match="must be BUY or SELL"):
        plan(signal=Signal.HOLD)


def test_pending_plan_rejects_nonpositive_prices() -> None:
    with pytest.raises(ValueError, match="prices must be positive"):
        plan(trigger_price=0.0)


def test_pending_plan_rejects_invalid_score() -> None:
    with pytest.raises(ValueError, match="between zero and one"):
        plan(score=1.1)


def test_pending_plan_rejects_invalid_wait_bars() -> None:
    with pytest.raises(ValueError, match="wait bars must be positive"):
        plan(maximum_wait_bars=0)


def test_pending_plan_rejects_invalid_buy_protection() -> None:
    with pytest.raises(ValueError, match="BUY pending protection"):
        plan(stop_loss=101.0)


def test_pending_plan_rejects_invalid_sell_protection() -> None:
    with pytest.raises(ValueError, match="SELL pending protection"):
        plan(
            signal=Signal.SELL,
            order_type=PendingOrderType.SELL_STOP,
            trigger_price=100.0,
            stop_loss=99.0,
            take_profit=98.0,
        )


def test_valid_sell_pending_plan() -> None:
    result = plan(
        signal=Signal.SELL,
        order_type=PendingOrderType.SELL_STOP,
        trigger_price=100.0,
        stop_loss=102.0,
        take_profit=98.0,
    )
    assert result.signal is Signal.SELL

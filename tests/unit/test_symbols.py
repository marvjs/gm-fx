"""Forex symbol domain tests."""

import pytest

from grandmaster_fx.domain.symbols import ForexIdentity, SymbolSnapshot, choose_symbol
from grandmaster_fx.exceptions import Mt5DataError

ALLOWED = frozenset({"EUR", "USD", "JPY", "GBP"})


def raw(**updates: object) -> dict[str, object]:
    values = {
        "name": "EURUSDm",
        "currency_base": "EUR",
        "currency_profit": "USD",
        "description": "Euro",
        "select": False,
        "visible": False,
        "trade_mode": 4,
        "digits": 5,
        "point": 0.00001,
        "spread": 10,
        "spread_float": True,
        "trade_tick_size": 0.00001,
        "trade_tick_value": 1.0,
        "trade_contract_size": 100000,
        "volume_min": 0.01,
        "volume_max": 100.0,
        "volume_step": 0.01,
        "volume_limit": 0.0,
        "trade_stops_level": 0,
        "trade_freeze_level": 0,
    }
    values.update(updates)
    return values


def test_identity_rejects_non_currency() -> None:
    assert ForexIdentity.detect("XAUUSD", "XAU", "USD", ALLOWED) is None


def test_snapshot_and_volume_normalization() -> None:
    item = SymbolSnapshot.from_mapping(raw(), ALLOWED)
    assert item is not None
    assert item.identity.normalized == "EURUSD"
    assert item.normalize_volume(0.127) == 0.12
    assert item.spread_price == pytest.approx(0.0001)


def test_choose_prefers_visible_exact_candidate() -> None:
    hidden = SymbolSnapshot.from_mapping(raw(), ALLOWED)
    visible = SymbolSnapshot.from_mapping(raw(name="EURUSD", visible=True, select=True), ALLOWED)
    assert hidden is not None
    assert visible is not None
    assert choose_symbol([hidden, visible], "eurusd") is visible


def test_choose_missing_raises() -> None:
    with pytest.raises(Mt5DataError, match="No broker symbol"):
        choose_symbol([], "EURUSD")


def test_incomplete_symbol_raises() -> None:
    with pytest.raises(Mt5DataError, match="incomplete symbol"):
        SymbolSnapshot.from_mapping(
            {"name": "EURUSD", "currency_base": "EUR", "currency_profit": "USD"}, ALLOWED
        )

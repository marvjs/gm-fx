"""Forex symbol classification, normalization, and broker snapshots."""

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import ROUND_FLOOR, Decimal
from typing import Any

from grandmaster_fx.exceptions import Mt5DataError

TRADE_MODE_DISABLED = 0


@dataclass(frozen=True, slots=True)
class ForexIdentity:
    """Normalized currency-pair identity."""

    normalized: str
    base: str
    quote: str

    @classmethod
    def detect(
        cls, name: str, base: str, quote: str, allowed: frozenset[str]
    ) -> "ForexIdentity | None":
        base, quote = base.upper(), quote.upper()
        if base not in allowed or quote not in allowed or base == quote:
            return None
        normalized = base + quote
        if normalized not in name.upper():
            return None
        return cls(normalized, base, quote)


@dataclass(frozen=True, slots=True)
class SymbolSnapshot:
    """Validated broker symbol metadata needed by later trading blocks."""

    name: str
    identity: ForexIdentity
    description: str
    selected: bool
    visible: bool
    trade_mode: int
    digits: int
    point: float
    spread_points: int
    spread_float: bool
    tick_size: float
    tick_value: float
    contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    volume_limit: float
    stops_level: int
    freeze_level: int

    @classmethod
    def from_mapping(
        cls, values: Mapping[str, Any], allowed: frozenset[str]
    ) -> "SymbolSnapshot | None":
        try:
            identity = ForexIdentity.detect(
                str(values["name"]),
                str(values["currency_base"]),
                str(values["currency_profit"]),
                allowed,
            )
            if identity is None:
                return None
            return cls(
                name=str(values["name"]),
                identity=identity,
                description=str(values.get("description", "")),
                selected=bool(values["select"]),
                visible=bool(values["visible"]),
                trade_mode=int(values["trade_mode"]),
                digits=int(values["digits"]),
                point=float(values["point"]),
                spread_points=int(values["spread"]),
                spread_float=bool(values["spread_float"]),
                tick_size=float(values["trade_tick_size"]),
                tick_value=float(values["trade_tick_value"]),
                contract_size=float(values["trade_contract_size"]),
                volume_min=float(values["volume_min"]),
                volume_max=float(values["volume_max"]),
                volume_step=float(values["volume_step"]),
                volume_limit=float(values["volume_limit"]),
                stops_level=int(values["trade_stops_level"]),
                freeze_level=int(values["trade_freeze_level"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise Mt5DataError(f"MT5 returned incomplete symbol information: {error}") from error

    @property
    def trade_enabled(self) -> bool:
        return self.trade_mode != TRADE_MODE_DISABLED

    @property
    def spread_price(self) -> float:
        return self.spread_points * self.point

    def normalize_volume(self, requested: float) -> float:
        """Floor volume to broker step and clamp it to broker bounds."""
        value = min(
            max(Decimal(str(requested)), Decimal(str(self.volume_min))),
            Decimal(str(self.volume_max)),
        )
        step = Decimal(str(self.volume_step))
        units = (value / step).to_integral_value(rounding=ROUND_FLOOR)
        return float(units * step)


def choose_symbol(candidates: list[SymbolSnapshot], normalized: str) -> SymbolSnapshot:
    """Resolve one normalized pair deterministically, preferring visible/selectable names."""
    matches = [item for item in candidates if item.identity.normalized == normalized.upper()]
    if not matches:
        raise Mt5DataError(f"No broker symbol resolves to {normalized.upper()}")
    return sorted(
        matches, key=lambda item: (not item.visible, not item.selected, len(item.name), item.name)
    )[0]

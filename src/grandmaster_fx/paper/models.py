"""Persistent paper account models."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from grandmaster_fx.strategies.models import Signal


@dataclass(slots=True)
class PaperPosition:
    symbol: str
    signal: Signal
    entry: float
    current: float
    stop_loss: float
    take_profit: float
    point: float
    cash_per_point: float
    score: float
    opened_at: str
    high_water_cash: float = 0.0

    @property
    def profit(self) -> float:
        direction = 1.0 if self.signal is Signal.BUY else -1.0
        return direction * (self.current - self.entry) / self.point * self.cash_per_point

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["signal"] = self.signal.value
        return result

    @classmethod
    def from_dict(cls, values: dict[str, Any]) -> PaperPosition:
        return cls(**{**values, "signal": Signal(values["signal"])})


@dataclass(slots=True)
class PaperState:
    balance: float
    realized_profit: float = 0.0
    positions: list[PaperPosition] = field(default_factory=list)
    cooldowns: dict[str, str] = field(default_factory=dict)
    updated_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def floating_profit(self) -> float:
        return sum(item.profit for item in self.positions)

    @property
    def equity(self) -> float:
        return self.balance + self.floating_profit

"""Immutable demo execution domain models."""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from grandmaster_fx.strategies.models import Signal


class CloseReason(StrEnum):
    SMALL_PROFIT = "small_profit"
    PROFIT_RETRACEMENT = "profit_retracement"
    FLOATING_LOSS_LIMIT = "floating_loss_limit"
    EMERGENCY_STOP = "emergency_stop"


@dataclass(frozen=True, slots=True)
class ExecutionCandidate:
    symbol: str
    signal: Signal
    score: float
    stop_loss: float
    take_profit: float

    def __post_init__(self) -> None:
        if self.signal is Signal.HOLD:
            message = "execution candidate must be BUY or SELL"
            raise ValueError(message)
        if not 0 <= self.score <= 1:
            message = "candidate score must be between zero and one"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    ticket: int
    symbol: str
    signal: Signal
    volume: float
    price_open: float
    price_current: float
    stop_loss: float
    take_profit: float
    profit: float
    magic: int
    opened_at: datetime

    @classmethod
    def from_mapping(cls, values: Mapping[str, Any]) -> "PositionSnapshot":
        position_type = int(values["type"])
        return cls(
            ticket=int(values["ticket"]),
            symbol=str(values["symbol"]),
            signal=Signal.BUY if position_type == 0 else Signal.SELL,
            volume=float(values["volume"]),
            price_open=float(values["price_open"]),
            price_current=float(values["price_current"]),
            stop_loss=float(values["sl"]),
            take_profit=float(values["tp"]),
            profit=float(values["profit"]),
            magic=int(values["magic"]),
            opened_at=datetime.fromtimestamp(int(values["time"]), UTC),
        )


@dataclass(slots=True)
class ProfitTrail:
    high_water_cash: float = 0.0

    def update(
        self, profit: float, activation: float, retracement: float, target: float
    ) -> CloseReason | None:
        self.high_water_cash = max(self.high_water_cash, profit)
        if profit >= target:
            return CloseReason.SMALL_PROFIT
        if self.high_water_cash >= activation and self.high_water_cash - profit >= retracement:
            return CloseReason.PROFIT_RETRACEMENT
        return None

"""Broker-neutral pending-order plans and lifecycle models."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.strategies.models import Signal


class PendingOrderType(StrEnum):
    """Supported broker-neutral entry instructions."""

    BUY_STOP = "buy_stop"
    SELL_STOP = "sell_stop"
    BUY_LIMIT = "buy_limit"
    SELL_LIMIT = "sell_limit"


class PendingOrderState(StrEnum):
    """Lifecycle state shared by paper and broker adapters."""

    PROPOSED = "proposed"
    VALIDATED = "validated"
    ACTIVE = "active"
    TRIGGERED = "triggered"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"
    INVALIDATED = "invalidated"


@dataclass(frozen=True, slots=True)
class PendingOrderPlan:
    """Complete broker-neutral instruction produced by shared analysis."""

    identity: str
    strategy_id: str
    symbol: str
    timeframe: Timeframe
    signal: Signal
    order_type: PendingOrderType
    source_time: datetime
    trigger_price: float
    stop_loss: float
    take_profit: float
    maximum_wait_bars: int
    score: float

    def __post_init__(self) -> None:
        if self.signal is Signal.HOLD:
            message = "pending order plan must be BUY or SELL"
            raise ValueError(message)
        if min(self.trigger_price, self.stop_loss, self.take_profit) <= 0:
            message = "pending order prices must be positive"
            raise ValueError(message)
        if not 0 <= self.score <= 1:
            message = "pending order score must be between zero and one"
            raise ValueError(message)
        if self.maximum_wait_bars <= 0:
            message = "pending order wait bars must be positive"
            raise ValueError(message)
        if self.signal is Signal.BUY and not self.stop_loss < self.trigger_price < self.take_profit:
            message = "BUY pending protection must satisfy stop < trigger < target"
            raise ValueError(message)
        if (
            self.signal is Signal.SELL
            and not self.take_profit < self.trigger_price < self.stop_loss
        ):
            message = "SELL pending protection must satisfy target < trigger < stop"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class PendingOrderRecord:
    """Persisted pending-order state for paper and future profile adapters."""

    plan: PendingOrderPlan
    state: PendingOrderState
    created_at: datetime
    updated_at: datetime
    age_bars: int = 0
    triggered_at: datetime | None = None
    triggered_price: float | None = None
    reason: str = "created"

    def __post_init__(self) -> None:
        if self.age_bars < 0:
            message = "pending order age bars cannot be negative"
            raise ValueError(message)
        if self.state is PendingOrderState.TRIGGERED and (
            self.triggered_at is None or self.triggered_price is None
        ):
            message = "triggered pending order requires trigger time and price"
            raise ValueError(message)


@dataclass(frozen=True, slots=True)
class PendingEvaluation:
    """One deterministic pending-order lifecycle evaluation."""

    record: PendingOrderRecord
    changed: bool

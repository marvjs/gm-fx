"""Atomic live pending-order ownership and reconciliation registry."""

import json
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class LivePendingState(StrEnum):
    """Observed broker state for an owned live pending order."""

    ACTIVE = "active"
    TRIGGERED = "triggered"
    FILLED = "filled"
    CANCELED = "canceled"
    EXPIRED = "expired"
    REJECTED = "rejected"
    EXTERNALLY_MODIFIED = "externally_modified"
    MISSING = "missing"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class LivePendingRecord:
    """Persistent identity-to-ticket ownership record."""

    identity: str
    ticket: int
    strategy_id: str
    symbol: str
    timeframe: str
    direction: str
    order_type: str
    source_time: str
    trigger_price: float
    stop_loss: float
    take_profit: float
    volume: float
    expiration: str
    magic: int
    comment: str
    placed_at: str
    reconciled_at: str
    state: LivePendingState
    detail: str = "confirmed_by_broker"


class LivePendingRegistry:
    """Atomic JSON registry isolated to the live execution profile."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> tuple[LivePendingRecord, ...]:
        if not self.path.exists():
            return ()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return tuple(
            LivePendingRecord(**{**item, "state": LivePendingState(str(item["state"]))})
            for item in payload
        )

    def save(self, records: tuple[LivePendingRecord, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps([asdict(item) for item in records], indent=2, default=str),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    def upsert(self, record: LivePendingRecord) -> None:
        existing = list(self.load())
        for index, item in enumerate(existing):
            if item.ticket == record.ticket or item.identity == record.identity:
                existing[index] = record
                break
        else:
            existing.append(record)
        self.save(tuple(existing))

    def reconcile(
        self,
        records: tuple[LivePendingRecord, ...],
    ) -> tuple[LivePendingRecord, ...]:
        now = datetime.now(UTC).isoformat()
        updated = tuple(replace(item, reconciled_at=now) for item in records)
        self.save(updated)
        return updated

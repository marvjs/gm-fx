"""Atomic JSON persistence for pending paper orders."""

import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.pending.models import (
    PendingOrderPlan,
    PendingOrderRecord,
    PendingOrderState,
    PendingOrderType,
)
from grandmaster_fx.strategies.models import Signal


class PendingOrderStore:
    """Restart-safe pending-order persistence keyed by deterministic identity."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> tuple[PendingOrderRecord, ...]:
        if not self.path.exists():
            return ()
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        return tuple(self._decode(item) for item in payload)

    def save(self, records: tuple[PendingOrderRecord, ...]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps([self._encode(item) for item in records], indent=2),
            encoding="utf-8",
        )
        temporary.replace(self.path)

    @staticmethod
    def _encode(record: PendingOrderRecord) -> dict[str, object]:
        payload = asdict(record)
        plan = payload["plan"]
        if not isinstance(plan, dict):
            message = "pending plan serialization failed"
            raise TypeError(message)
        plan["timeframe"] = record.plan.timeframe.value
        plan["signal"] = record.plan.signal.value
        plan["order_type"] = record.plan.order_type.value
        plan["source_time"] = record.plan.source_time.isoformat()
        payload["state"] = record.state.value
        payload["created_at"] = record.created_at.isoformat()
        payload["updated_at"] = record.updated_at.isoformat()
        payload["triggered_at"] = (
            record.triggered_at.isoformat() if record.triggered_at is not None else None
        )
        return payload

    @staticmethod
    def _decode(payload: dict[str, object]) -> PendingOrderRecord:
        raw_plan = payload["plan"]
        if not isinstance(raw_plan, dict):
            message = "persisted pending order is missing its plan"
            raise TypeError(message)
        plan = PendingOrderPlan(
            identity=str(raw_plan["identity"]),
            strategy_id=str(raw_plan["strategy_id"]),
            symbol=str(raw_plan["symbol"]),
            timeframe=Timeframe(str(raw_plan["timeframe"])),
            signal=Signal(str(raw_plan["signal"])),
            order_type=PendingOrderType(str(raw_plan["order_type"])),
            source_time=datetime.fromisoformat(str(raw_plan["source_time"])),
            trigger_price=float(raw_plan["trigger_price"]),
            stop_loss=float(raw_plan["stop_loss"]),
            take_profit=float(raw_plan["take_profit"]),
            maximum_wait_bars=int(raw_plan["maximum_wait_bars"]),
            score=float(raw_plan["score"]),
        )
        triggered_at = payload.get("triggered_at")
        raw_age_bars = payload.get("age_bars", 0)
        raw_triggered_price = payload.get("triggered_price")
        if not isinstance(raw_age_bars, int):
            message = "persisted pending order age bars must be an integer"
            raise TypeError(message)
        if raw_triggered_price is not None and not isinstance(raw_triggered_price, (int, float)):
            message = "persisted pending trigger price must be numeric"
            raise TypeError(message)
        return PendingOrderRecord(
            plan=plan,
            state=PendingOrderState(str(payload["state"])),
            created_at=datetime.fromisoformat(str(payload["created_at"])),
            updated_at=datetime.fromisoformat(str(payload["updated_at"])),
            age_bars=raw_age_bars,
            triggered_at=(
                datetime.fromisoformat(str(triggered_at)) if triggered_at is not None else None
            ),
            triggered_price=(
                float(raw_triggered_price) if raw_triggered_price is not None else None
            ),
            reason=str(payload.get("reason", "restored")),
        )

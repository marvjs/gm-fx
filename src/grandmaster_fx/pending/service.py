"""Shared duplicate reconciliation and persistent pending-order service."""

from datetime import UTC, datetime

from grandmaster_fx.pending.models import PendingOrderPlan, PendingOrderRecord, PendingOrderState
from grandmaster_fx.pending.store import PendingOrderStore


class PendingOrderService:
    """Profile-independent management of broker-neutral pending orders."""

    def __init__(self, store: PendingOrderStore) -> None:
        self.store = store

    def list(self) -> tuple[PendingOrderRecord, ...]:
        return self.store.load()

    def active(self) -> tuple[PendingOrderRecord, ...]:
        return tuple(item for item in self.list() if item.state is PendingOrderState.ACTIVE)

    def find_duplicate(self, plan: PendingOrderPlan) -> PendingOrderRecord | None:
        for record in self.active():
            if record.plan.identity == plan.identity:
                return record
            if (
                record.plan.strategy_id == plan.strategy_id
                and record.plan.symbol == plan.symbol
                and record.plan.timeframe is plan.timeframe
                and record.plan.signal is plan.signal
            ):
                return record
        return None

    def place(self, plan: PendingOrderPlan) -> tuple[PendingOrderRecord, bool]:
        duplicate = self.find_duplicate(plan)
        if duplicate is not None:
            return duplicate, False
        now = datetime.now(UTC)
        record = PendingOrderRecord(
            plan=plan,
            state=PendingOrderState.ACTIVE,
            created_at=now,
            updated_at=now,
            reason="paper_pending_order_placed",
        )
        records = (*self.list(), record)
        self.store.save(records)
        return record, True

    def replace(self, record: PendingOrderRecord) -> None:
        records = tuple(
            record if item.plan.identity == record.plan.identity else item for item in self.list()
        )
        self.store.save(records)

    def cancel(self, identity: str) -> PendingOrderRecord | None:
        """Cancel one active paper pending order by deterministic identity."""
        now = datetime.now(UTC)
        selected: PendingOrderRecord | None = None
        records: list[PendingOrderRecord] = []
        for item in self.list():
            if item.plan.identity == identity and item.state is PendingOrderState.ACTIVE:
                selected = PendingOrderRecord(
                    plan=item.plan,
                    state=PendingOrderState.CANCELED,
                    created_at=item.created_at,
                    updated_at=now,
                    age_bars=item.age_bars,
                    reason="paper_pending_order_canceled",
                )
                records.append(selected)
            else:
                records.append(item)
        self.store.save(tuple(records))
        return selected

"""Demo-only multi-symbol order and profit-trailing manager."""

from datetime import UTC, datetime, timedelta
from typing import Protocol

from grandmaster_fx.config.demo_execution import DemoExecutionSettings
from grandmaster_fx.domain.mt5 import AccountSnapshot
from grandmaster_fx.execution.journal import ExecutionJournal
from grandmaster_fx.execution.models import (
    CloseReason,
    ExecutionCandidate,
    PositionSnapshot,
    ProfitTrail,
)


class ExecutionGateway(Protocol):
    def account(self) -> AccountSnapshot: ...
    def positions(self, magic: int) -> list[PositionSnapshot]: ...
    def open_demo_order(
        self,
        candidate: ExecutionCandidate,
        volume: float,
        magic: int,
        comment: str,
        deviation: int,
        dry_run: bool,  # noqa: FBT001
    ) -> int | None: ...
    def close_demo_position(
        self,
        position: PositionSnapshot,
        magic: int,
        comment: str,
        deviation: int,
        dry_run: bool,  # noqa: FBT001
    ) -> bool: ...


class DemoExecutionManager:
    def __init__(
        self,
        gateway: ExecutionGateway,
        settings: DemoExecutionSettings,
        journal: ExecutionJournal | None = None,
    ) -> None:
        self.gateway = gateway
        self.settings = settings
        self.journal = journal or ExecutionJournal()
        self._trails: dict[int, ProfitTrail] = {}
        self._cooldowns: dict[str, datetime] = {}
        self._day_start_balance: float | None = None

    def _require_demo(self) -> AccountSnapshot:
        account = self.gateway.account()
        account.require_demo()
        if self._day_start_balance is None:
            self._day_start_balance = account.balance
        return account

    def monitor(self) -> tuple[int, ...]:
        account = self._require_demo()
        positions = self.gateway.positions(self.settings.execution.magic)
        if (
            self._day_start_balance is not None
            and account.equity
            <= self._day_start_balance - self.settings.risk.maximum_daily_loss_cash
        ):
            reasons = {item.ticket: CloseReason.EMERGENCY_STOP for item in positions}
        elif (
            sum(item.profit for item in positions) <= -self.settings.risk.maximum_floating_loss_cash
        ):
            reasons = {item.ticket: CloseReason.FLOATING_LOSS_LIMIT for item in positions}
        else:
            reasons = {}
            for position in positions:
                trail = self._trails.setdefault(position.ticket, ProfitTrail())
                reason = trail.update(
                    position.profit,
                    self.settings.profit.trailing_activation_cash,
                    self.settings.profit.trailing_retracement_cash,
                    self.settings.profit.small_profit_cash,
                )
                if reason is not None:
                    reasons[position.ticket] = reason
        closed: list[int] = []
        for position in positions:
            reason = reasons.get(position.ticket)
            if reason is None:
                continue
            if self.gateway.close_demo_position(
                position,
                self.settings.execution.magic,
                self.settings.execution.comment,
                self.settings.execution.deviation_points,
                self.settings.execution.dry_run,
            ):
                closed.append(position.ticket)
                self._trails.pop(position.ticket, None)
                self._cooldowns[position.symbol] = datetime.now(UTC) + timedelta(
                    seconds=self.settings.execution.cooldown_seconds
                )
                self.journal.append(
                    "position_closed",
                    ticket=position.ticket,
                    symbol=position.symbol,
                    reason=reason.value,
                    profit=position.profit,
                )
        return tuple(closed)

    def execute(self, candidates: list[ExecutionCandidate]) -> tuple[str, ...]:
        self._require_demo()
        positions = self.gateway.positions(self.settings.execution.magic)
        open_symbols = {item.symbol for item in positions}
        capacity = self.settings.execution.maximum_open_positions - len(positions)
        if capacity <= 0 or not self.settings.execution.enabled:
            return ()
        now = datetime.now(UTC)
        ranked = sorted(candidates, key=lambda item: item.score, reverse=True)
        opened: list[str] = []
        for candidate in ranked:
            if len(opened) >= capacity or candidate.symbol in open_symbols:
                continue
            if self._cooldowns.get(candidate.symbol, now) > now:
                continue
            ticket = self.gateway.open_demo_order(
                candidate,
                self.settings.risk.fixed_volume,
                self.settings.execution.magic,
                self.settings.execution.comment,
                self.settings.execution.deviation_points,
                self.settings.execution.dry_run,
            )
            opened.append(candidate.symbol)
            open_symbols.add(candidate.symbol)
            self.journal.append(
                "position_opened",
                ticket=ticket,
                symbol=candidate.symbol,
                signal=candidate.signal.value,
                score=candidate.score,
                dry_run=self.settings.execution.dry_run,
            )
        return tuple(opened)

"""Continuous, broker-free, multi-symbol paper execution worker."""

from __future__ import annotations

import json
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from statistics import fmean
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from grandmaster_fx.domain.market_data import Bar, Tick, Timeframe
    from grandmaster_fx.paper.config import PaperWorkerSettings
from grandmaster_fx.paper.models import PaperPosition, PaperState
from grandmaster_fx.paper.state import PaperStateStore
from grandmaster_fx.strategies.models import Signal


class PaperMarket(Protocol):
    def tick(self, name: str) -> Tick: ...
    def bars(self, name: str, timeframe: Timeframe, count: int, start: int = 1) -> list[Bar]: ...


class PaperWorker:
    def __init__(
        self,
        market: PaperMarket,
        symbols: tuple[tuple[str, float], ...],
        settings: PaperWorkerSettings,
        store: PaperStateStore | None = None,
        stop_path: Path = Path("data/paper/STOP"),
    ) -> None:
        self.market = market
        self.symbols = symbols
        self.settings = settings
        self.store = store or PaperStateStore()
        self.stop_path = stop_path

    def status(self) -> dict[str, object]:
        state = self.store.load(self.settings.paper.initial_balance)
        return {
            "balance": state.balance,
            "equity": state.equity,
            "realized_profit": state.realized_profit,
            "floating_profit": state.floating_profit,
            "positions": [item.to_dict() | {"profit": item.profit} for item in state.positions],
            "stop_requested": self.stop_path.exists(),
        }

    def cycle(self) -> dict[str, object]:
        state = self.store.load(self.settings.paper.initial_balance)
        closed = self._monitor(state)
        opened = self._scan(state)
        state.updated_at = datetime.now(UTC).isoformat()
        self.store.save(state)
        return {"closed": closed, "opened": opened, **self.status()}

    def run(self, maximum_cycles: int | None = None) -> None:
        self.stop_path.unlink(missing_ok=True)
        cycles = 0
        while not self.stop_path.exists():
            sys.stdout.write(json.dumps(self.cycle(), default=str) + "\n")
            cycles += 1
            if maximum_cycles is not None and cycles >= maximum_cycles:
                break
            time.sleep(self.settings.worker.poll_interval_seconds)

    def request_stop(self) -> None:
        self.stop_path.parent.mkdir(parents=True, exist_ok=True)
        self.stop_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")

    def _monitor(self, state: PaperState) -> list[str]:
        retained: list[PaperPosition] = []
        closed: list[str] = []
        now = datetime.now(UTC)
        for position in state.positions:
            tick = self.market.tick(position.symbol)
            position.current = tick.bid if position.signal is Signal.BUY else tick.ask
            position.high_water_cash = max(position.high_water_cash, position.profit)
            retraced = (
                position.high_water_cash >= self.settings.paper.trailing_activation_cash
                and position.high_water_cash - position.profit
                >= self.settings.paper.trailing_retracement_cash
            )
            target = position.profit >= self.settings.paper.small_profit_cash
            stopped = position.profit <= -self.settings.paper.stop_loss_cash
            price_stop = (
                position.current <= position.stop_loss
                if position.signal is Signal.BUY
                else position.current >= position.stop_loss
            )
            price_target = (
                position.current >= position.take_profit
                if position.signal is Signal.BUY
                else position.current <= position.take_profit
            )
            if target or retraced or stopped or price_stop or price_target:
                state.balance += position.profit
                state.realized_profit += position.profit
                state.cooldowns[position.symbol] = (
                    now + timedelta(seconds=self.settings.worker.cooldown_seconds)
                ).isoformat()
                closed.append(position.symbol)
            else:
                retained.append(position)
        state.positions = retained
        return closed

    def _scan(self, state: PaperState) -> list[str]:
        capacity = self.settings.worker.maximum_positions - len(state.positions)
        if capacity <= 0:
            return []
        open_symbols = {item.symbol for item in state.positions}
        now = datetime.now(UTC)
        candidates: list[PaperPosition] = []
        for symbol, point in self.symbols:
            if symbol in open_symbols:
                continue
            cooldown = state.cooldowns.get(symbol)
            if cooldown and datetime.fromisoformat(cooldown) > now:
                continue
            candidate = self._candidate(symbol, point)
            if candidate is not None:
                candidates.append(candidate)
        candidates.sort(key=lambda item: item.score, reverse=True)
        selected = candidates[:capacity]
        state.positions.extend(selected)
        return [item.symbol for item in selected]

    def _candidate(self, symbol: str, point: float) -> PaperPosition | None:
        bars = self.market.bars(
            symbol, self.settings.worker.timeframe, self.settings.worker.history_bars
        )
        required = max(self.settings.signal.slow_period, self.settings.signal.momentum_period + 1)
        if len(bars) < required:
            return None
        closes = [item.close for item in bars]
        fast = fmean(closes[-self.settings.signal.fast_period :])
        slow = fmean(closes[-self.settings.signal.slow_period :])
        previous = closes[-self.settings.signal.momentum_period - 1]
        momentum = (closes[-1] / previous - 1.0) * 100.0
        if fast > slow and momentum >= self.settings.signal.minimum_momentum_percent:
            signal = Signal.BUY
        elif fast < slow and momentum <= -self.settings.signal.minimum_momentum_percent:
            signal = Signal.SELL
        else:
            return None
        ranges = [item.high - item.low for item in bars[-14:]]
        atr = fmean(ranges)
        trend_strength = min(1.0, abs(fast - slow) / max(atr, point))
        momentum_strength = min(
            1.0, abs(momentum) / max(self.settings.signal.minimum_momentum_percent * 3, 0.0001)
        )
        score = (trend_strength + momentum_strength) / 2
        if score < self.settings.worker.minimum_score:
            return None
        tick = self.market.tick(symbol)
        entry = tick.ask if signal is Signal.BUY else tick.bid
        stop_distance = atr * self.settings.signal.stop_atr_multiple
        target_distance = atr * self.settings.signal.target_atr_multiple
        stop_loss = entry - stop_distance if signal is Signal.BUY else entry + stop_distance
        take_profit = entry + target_distance if signal is Signal.BUY else entry - target_distance
        return PaperPosition(
            symbol,
            signal,
            entry,
            entry,
            stop_loss,
            take_profit,
            point,
            self.settings.paper.cash_per_point,
            score,
            datetime.now(UTC).isoformat(),
        )

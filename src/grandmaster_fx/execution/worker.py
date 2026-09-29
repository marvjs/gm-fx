"""Continuous demo execution worker."""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.exceptions import Mt5DataError
from grandmaster_fx.execution.manager import DemoExecutionManager
from grandmaster_fx.execution.models import ExecutionCandidate
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway
from grandmaster_fx.market_data.service import MarketDataService
from grandmaster_fx.strategies.protocol import ResearchStrategy


class DemoWorker:
    """Continuously poll Mt5Gateway, evaluate strategies, and manage live demo execution."""

    def __init__(
        self,
        gateway: Mt5Gateway,
        manager: DemoExecutionManager,
        strategy: ResearchStrategy,
        timeframe: Timeframe,
        symbols: tuple[str, ...],
        allowed_currencies: frozenset[str],
        stop_path: Path = Path("data/execution/STOP"),
    ) -> None:
        self.gateway = gateway
        self.manager = manager
        self.strategy = strategy
        self.timeframe = timeframe
        self.symbols = symbols
        self.allowed_currencies = allowed_currencies
        self.stop_path = stop_path
        if gateway is not None:
            self.service = MarketDataService(gateway, allowed_currencies)

    def status(self) -> dict[str, object]:
        """Return the current account state and tracked positions."""
        account = self.gateway.account()
        positions = self.gateway.positions(self.manager.settings.execution.magic)
        return {
            "balance": account.balance,
            "equity": account.equity,
            "margin": account.margin,
            "positions": [
                {
                    "ticket": position.ticket,
                    "symbol": position.symbol,
                    "signal": position.signal.value,
                    "volume": position.volume,
                    "profit": position.profit,
                    "price_open": position.price_open,
                    "price_current": position.price_current,
                }
                for position in positions
            ],
            "stop_requested": self.stop_path.exists(),
        }

    def cycle(self) -> dict[str, object]:
        """Run one complete monitor-close and scanning-open sequence."""
        closed = self.manager.monitor()
        candidates: list[ExecutionCandidate] = []
        for pair in self.symbols:
            try:
                name, bars = self.service.bars(
                    pair, self.timeframe, max(120, self.strategy.minimum_bars)
                )
                metadata = self.gateway.symbol(name, self.allowed_currencies)
                decision = self.strategy.evaluate(name, bars, metadata.point)
                if (
                    decision.actionable
                    and decision.stop_loss is not None
                    and decision.take_profit is not None
                ):
                    score = min(1.0, max(0.0, decision.reward_risk or 1.0))
                    candidates.append(
                        ExecutionCandidate(
                            symbol=name,
                            signal=decision.signal,
                            score=score,
                            stop_loss=decision.stop_loss,
                            take_profit=decision.take_profit,
                        )
                    )
            except (ValueError, Mt5DataError):
                # Ignore symbol-specific evaluation failures (e.g. missing bars)
                continue
        opened = self.manager.execute(candidates)
        return {"closed": closed, "opened": opened, **self.status()}

    def run(self, maximum_cycles: int | None = None) -> None:
        """Continuously loop the execution cycle using the configured poll interval."""
        self.stop_path.unlink(missing_ok=True)
        cycles = 0
        interval = self.manager.settings.execution.poll_interval_seconds
        while not self.stop_path.exists():
            sys.stdout.write(json.dumps(self.cycle(), default=str) + "\n")
            sys.stdout.flush()
            cycles += 1
            if maximum_cycles is not None and cycles >= maximum_cycles:
                break
            time.sleep(interval)

    def request_stop(self) -> None:
        """Create the stop signal file to terminate any running cycle."""
        self.stop_path.parent.mkdir(parents=True, exist_ok=True)
        self.stop_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")

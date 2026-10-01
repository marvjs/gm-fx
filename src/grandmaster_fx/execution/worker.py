"""Continuous universal execution worker."""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

from rich.live import Live

from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.exceptions import Mt5DataError
from grandmaster_fx.execution.dashboard import render_dashboard
from grandmaster_fx.execution.manager import ExecutionManager
from grandmaster_fx.execution.models import ExecutionCandidate
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway
from grandmaster_fx.market_data.service import MarketDataService
from grandmaster_fx.strategies.protocol import ResearchStrategy

if TYPE_CHECKING:
    from grandmaster_fx.predictions.engine import PredictionEngine
    from grandmaster_fx.predictions.filters import TradeDirection


class ExecutionWorker:
    """Continuously poll Mt5Gateway, evaluate strategies, and manage live execution."""

    def __init__(
        self,
        gateway: Mt5Gateway,
        manager: ExecutionManager,
        strategy: ResearchStrategy,
        timeframe: Timeframe,
        symbols: tuple[str, ...],
        allowed_currencies: frozenset[str],
        stop_path: Path = Path("data/execution/STOP"),
        prediction_engine: "PredictionEngine | None" = None,
        strategy_id: str | None = None,
        consumed_path: Path = Path("data/execution/consumed_predictions.json"),
        direction: "TradeDirection | None" = None,
        profile: str = "demo",
    ) -> None:
        self.gateway = gateway
        self.manager = manager
        self.strategy = strategy
        self.timeframe = timeframe
        self.symbols = symbols
        self.allowed_currencies = allowed_currencies
        self.stop_path = stop_path
        self.prediction_engine = prediction_engine
        self.strategy_id = strategy_id or strategy.identifier
        self.consumed_path = consumed_path
        self.direction = direction
        self.profile = profile
        self.service = MarketDataService(gateway, allowed_currencies)

    def status(self) -> dict[str, object]:
        """Return the current account state and tracked positions."""
        account = self.gateway.account()
        positions = self.gateway.positions(self.manager.settings.execution.magic)
        terminal = self.gateway.terminal()
        return {
            "profile": self.profile,
            "account_mode": account.trade_mode.name,
            "login": account.login,
            "server": account.server,
            "balance": account.balance,
            "equity": account.equity,
            "profit": account.profit,
            "margin": account.margin,
            "margin_free": account.margin_free,
            "account_trade_allowed": account.trade_allowed,
            "expert_trade_allowed": account.trade_expert,
            "terminal_connected": terminal.connected,
            "terminal_trade_allowed": terminal.trade_allowed,
            "trade_api_enabled": not terminal.trade_api_disabled,
            "magic": self.manager.settings.execution.magic,
            "comment": self.manager.settings.execution.comment,
            "stop_path": str(self.stop_path),
            "consumed_path": str(self.consumed_path),
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

    def _load_consumed(self) -> set[str]:
        if not self.consumed_path.is_file():
            return set()
        try:
            values = json.loads(self.consumed_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            message = f"Consumed prediction state is invalid: {error}"
            raise Mt5DataError(message) from error
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            message = "Consumed prediction state has an invalid schema"
            raise Mt5DataError(message)
        return set(values)

    def _save_consumed(self, values: set[str]) -> None:
        self.consumed_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.consumed_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(sorted(values), indent=2), encoding="utf-8")
        temporary.replace(self.consumed_path)

    def cycle(self) -> dict[str, object]:
        """Run one monitor, prediction-gate, and execution sequence."""
        closed = self.manager.monitor()
        candidates: list[ExecutionCandidate] = []
        candidate_keys: dict[str, str] = {}
        predictions: list[dict[str, object]] = []
        consumed = self._load_consumed() if self.prediction_engine is not None else set()
        for pair in self.symbols:
            try:
                count = max(120, self.strategy.minimum_bars)
                name, bars = self.service.bars(pair, self.timeframe, count)
                metadata = self.gateway.symbol(name, self.allowed_currencies)
                decision = self.strategy.evaluate(name, bars, metadata.point)
                direction_allowed = self.direction is None or self.direction.allows(decision.signal)
                accepted = decision.actionable and direction_allowed
                report: dict[str, object] = {
                    "symbol": name,
                    "strategy_id": self.strategy_id,
                    "signal": decision.signal.value,
                    "timestamp": decision.timestamp.isoformat(),
                    "decision_reasons": [reason.value for reason in decision.reasons],
                    "primary_reason": decision.reasons[0].value if decision.reasons else "none",
                    "direction_allowed": direction_allowed,
                }
                if self.prediction_engine is not None:
                    higher = self.prediction_engine.settings.confirmation.higher_timeframe
                    _higher_name, higher_bars = self.service.bars(pair, higher, count)
                    assessment = self.prediction_engine.assess(
                        self.strategy_id, decision.signal, bars, higher_bars
                    )
                    key = (
                        f"{self.strategy_id}|{name}|{self.timeframe.value}|"
                        f"{decision.timestamp.isoformat()}|{decision.signal.value}"
                    )
                    duplicate = key in consumed
                    accepted = assessment.accepted and direction_allowed and not duplicate
                    report.update(
                        {
                            "regime": assessment.regime.regime.value,
                            "strategy_allowed": assessment.strategy_allowed,
                            "confirmation": assessment.confirmation.confirmed,
                            "confirmation_reason": assessment.confirmation.reason.value,
                            "duplicate": duplicate,
                        }
                    )
                    if accepted:
                        candidate_keys[name] = key
                report["accepted"] = accepted
                predictions.append(report)
                if (
                    accepted
                    and decision.entry is not None
                    and decision.stop_loss is not None
                    and decision.take_profit is not None
                ):
                    score = min(1.0, max(0.0, decision.reward_risk or 1.0))
                    candidates.append(
                        ExecutionCandidate(
                            symbol=name,
                            signal=decision.signal,
                            score=score,
                            entry=decision.entry,
                            stop_loss=decision.stop_loss,
                            take_profit=decision.take_profit,
                        )
                    )
            except (ValueError, Mt5DataError) as error:
                predictions.append(
                    {
                        "symbol": pair,
                        "strategy_id": self.strategy_id,
                        "signal": "ERROR",
                        "primary_reason": "evaluation_error",
                        "error": str(error),
                        "accepted": False,
                    }
                )
                self.manager.journal.append(
                    "evaluation_error",
                    profile=self.profile,
                    symbol=pair,
                    error=str(error),
                )
        opened = self.manager.execute(candidates)
        if self.prediction_engine is not None:
            consumed.update(candidate_keys[symbol] for symbol in opened if symbol in candidate_keys)
            self._save_consumed(consumed)
        return {
            "closed": closed,
            "opened": opened,
            "predictions": predictions,
            **self.status(),
        }

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

    def run_dashboard(
        self,
        strategy_id: str,
        maximum_cycles: int | None = None,
        title: str = "Grandmaster FX Demo Dashboard",
    ) -> None:
        """Run a single-screen Rich dashboard that refreshes in place."""
        self.stop_path.unlink(missing_ok=True)
        started_at = datetime.now(UTC)
        cycles = 0
        interval = self.manager.settings.execution.poll_interval_seconds
        with Live(
            console=__import__("grandmaster_fx.console", fromlist=["console"]).console,
            refresh_per_second=4,
            screen=True,
        ) as live:
            while not self.stop_path.exists():
                payload = self.cycle()
                cycles += 1
                live.update(
                    render_dashboard(
                        payload,
                        strategy=strategy_id,
                        timeframe=self.timeframe.value,
                        cycle_number=cycles,
                        started_at=started_at,
                        title=title,
                    ),
                    refresh=True,
                )
                if maximum_cycles is not None and cycles >= maximum_cycles:
                    break
                time.sleep(interval)

    def request_stop(self) -> None:
        """Create the stop signal file to terminate any running cycle."""
        self.stop_path.parent.mkdir(parents=True, exist_ok=True)
        self.stop_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")

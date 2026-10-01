"""Reusable symbol and direction filters for research and simulated execution."""

from dataclasses import replace
from enum import StrEnum

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.models import Signal, StrategyDecision
from grandmaster_fx.strategies.protocol import IndexedResearchStrategy, ResearchStrategy


class TradeDirection(StrEnum):
    """Allowed directional side for a candidate experiment."""

    ALL = "ALL"
    BUY = "BUY"
    SELL = "SELL"

    def allows(self, signal: Signal) -> bool:
        return self is TradeDirection.ALL or signal.value == self.value


class DirectionalStrategy:
    """Block disallowed directions while preserving indexed strategy evaluation."""

    def __init__(self, strategy: ResearchStrategy, direction: TradeDirection) -> None:
        self.strategy = strategy
        self.direction = direction

    @property
    def identifier(self) -> str:
        return self.strategy.identifier

    @property
    def minimum_bars(self) -> int:
        return self.strategy.minimum_bars

    def prepare(self, bars: list[Bar]) -> object:
        if isinstance(self.strategy, IndexedResearchStrategy):
            return self.strategy.prepare(bars)
        return None

    def _filter(self, decision: StrategyDecision) -> StrategyDecision:
        if not decision.actionable or self.direction.allows(decision.signal):
            return decision
        return replace(
            decision,
            signal=Signal.HOLD,
            entry=None,
            stop_loss=None,
            take_profit=None,
            reward_risk=None,
        )

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        return self._filter(self.strategy.evaluate(symbol, bars, point))

    def evaluate_at(
        self,
        symbol: str,
        bars: list[Bar],
        index: int,
        point: float,
        context: object,
    ) -> StrategyDecision:
        if isinstance(self.strategy, IndexedResearchStrategy) and context is not None:
            decision = self.strategy.evaluate_at(symbol, bars, index, point, context)
        else:
            decision = self.strategy.evaluate(symbol, bars[: index + 1], point)
        return self._filter(decision)

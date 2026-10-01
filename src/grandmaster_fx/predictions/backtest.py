"""No-lookahead prediction gate for historical strategy evaluation."""

from collections import Counter
from dataclasses import dataclass, replace
from datetime import datetime, timedelta

from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.predictions.engine import PredictionEngine
from grandmaster_fx.strategies.models import Signal, StrategyDecision
from grandmaster_fx.strategies.protocol import IndexedResearchStrategy, ResearchStrategy

_TIMEFRAME_MINUTES = {
    Timeframe.M1: 1,
    Timeframe.M5: 5,
    Timeframe.M15: 15,
    Timeframe.M30: 30,
    Timeframe.H1: 60,
}


@dataclass(frozen=True, slots=True)
class PredictionBacktestReport:
    primary_signals: int
    accepted_signals: int
    rejected_signals: int
    rejection_reasons: dict[str, int]
    regimes: dict[str, int]


class PredictionBacktestStrategy:
    """Apply regime selection and aligned higher-timeframe confirmation."""

    def __init__(
        self,
        strategy_id: str,
        strategy: ResearchStrategy,
        engine: PredictionEngine,
        higher_bars: list[Bar],
    ) -> None:
        self.strategy_id = strategy_id
        self.strategy = strategy
        self.engine = engine
        self.higher_bars = higher_bars
        self._primary_signals = 0
        self._accepted_signals = 0
        self._rejections: Counter[str] = Counter()
        self._regimes: Counter[str] = Counter()

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

    def _base_decision(
        self,
        symbol: str,
        bars: list[Bar],
        index: int,
        point: float,
        context: object,
    ) -> StrategyDecision:
        if isinstance(self.strategy, IndexedResearchStrategy) and context is not None:
            return self.strategy.evaluate_at(symbol, bars, index, point, context)
        return self.strategy.evaluate(symbol, bars[: index + 1], point)

    def _completed_higher_bars(self, decision_time: datetime) -> list[Bar]:
        higher = self.engine.settings.confirmation.higher_timeframe
        duration = timedelta(minutes=_TIMEFRAME_MINUTES[higher])
        return [item for item in self.higher_bars if item.time + duration <= decision_time]

    def evaluate_at(
        self,
        symbol: str,
        bars: list[Bar],
        index: int,
        point: float,
        context: object,
    ) -> StrategyDecision:
        decision = self._base_decision(symbol, bars, index, point, context)
        primary_history = bars[: index + 1]
        higher_history = self._completed_higher_bars(decision.timestamp)
        assessment = self.engine.assess(
            self.strategy_id,
            decision.signal,
            primary_history,
            higher_history,
        )
        self._regimes[assessment.regime.regime.value] += 1
        if not decision.actionable:
            return decision
        self._primary_signals += 1
        if assessment.accepted:
            self._accepted_signals += 1
            return decision
        if not assessment.strategy_allowed:
            reason = "strategy_not_allowed"
        else:
            reason = assessment.confirmation.reason.value
        self._rejections[reason] += 1
        return replace(
            decision,
            signal=Signal.HOLD,
            entry=None,
            stop_loss=None,
            take_profit=None,
            reward_risk=None,
        )

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        context = self.prepare(bars)
        return self.evaluate_at(symbol, bars, len(bars) - 1, point, context)

    def report(self) -> PredictionBacktestReport:
        return PredictionBacktestReport(
            primary_signals=self._primary_signals,
            accepted_signals=self._accepted_signals,
            rejected_signals=self._primary_signals - self._accepted_signals,
            rejection_reasons=dict(sorted(self._rejections.items())),
            regimes=dict(sorted(self._regimes.items())),
        )


def required_higher_bar_count(
    primary_count: int,
    primary: Timeframe,
    higher: Timeframe,
) -> int:
    """Return enough higher bars to span the primary history plus warmup."""
    ratio = _TIMEFRAME_MINUTES[primary] / _TIMEFRAME_MINUTES[higher]
    return max(200, int(primary_count * ratio) + 100)

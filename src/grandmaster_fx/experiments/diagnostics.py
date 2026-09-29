"""Decision reasons and stage-ordered filter funnels."""

from collections import Counter
from dataclasses import dataclass

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.models import Signal
from grandmaster_fx.strategies.protocol import (
    IndexedResearchStrategy,
    ResearchStrategy,
)

FUNNEL_STAGES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("session_eligible", ("outside_session",)),
    ("spread_eligible", ("spread_too_wide",)),
    (
        "volatility_eligible",
        ("volatility_too_low", "volatility_too_high"),
    ),
    ("compression_eligible", ("compression_not_confirmed",)),
    ("expansion_eligible", ("expansion_not_confirmed",)),
    ("breakout_eligible", ("breakout_not_confirmed",)),
    ("trend_eligible", ("trend_not_aligned",)),
)


@dataclass(frozen=True, slots=True)
class StrategyDiagnostics:
    """Activity, terminal reasons, and progressive filter survival."""

    bars_available: int
    bars_evaluated: int
    actionable_signals: int
    buy_signals: int
    sell_signals: int
    signal_frequency_percent: float
    reason_counts: dict[str, int]
    funnel_counts: dict[str, int]
    funnel_percentages: dict[str, float]


def _ordered_funnel(
    evaluated: int,
    actionable: int,
    reasons: dict[str, int],
) -> tuple[dict[str, int], dict[str, float]]:
    """Build a monotonic funnel in strategy evaluation order."""
    remaining = evaluated
    counts: dict[str, int] = {"bars_evaluated": evaluated}
    for stage, rejected_reasons in FUNNEL_STAGES:
        rejected = sum(reasons.get(reason, 0) for reason in rejected_reasons)
        remaining = max(0, remaining - rejected)
        counts[stage] = remaining
    counts["actionable"] = actionable

    previous = evaluated
    for stage, count in counts.items():
        if count > previous:
            message = f"Filter funnel is not monotonic at {stage}"
            raise ValueError(message)
        previous = count

    percentages = {
        stage: count / evaluated * 100 if evaluated else 0.0 for stage, count in counts.items()
    }
    return counts, percentages


def collect_diagnostics(
    strategy: ResearchStrategy,
    symbol: str,
    bars: list[Bar],
    point: float,
) -> StrategyDiagnostics:
    """Evaluate eligible candles once and count terminal decision reasons."""
    start = strategy.minimum_bars
    prepared = strategy.prepare(bars) if isinstance(strategy, IndexedResearchStrategy) else None
    reasons: Counter[str] = Counter()
    buys = 0
    sells = 0
    for index in range(start, len(bars)):
        if isinstance(strategy, IndexedResearchStrategy) and prepared is not None:
            decision = strategy.evaluate_at(symbol, bars, index, point, prepared)
        else:
            decision = strategy.evaluate(symbol, bars[: index + 1], point)
        reasons.update(reason.value for reason in decision.reasons)
        buys += decision.signal is Signal.BUY
        sells += decision.signal is Signal.SELL

    evaluated = max(0, len(bars) - start)
    actionable = buys + sells
    frequency = actionable / evaluated * 100 if evaluated else 0.0
    ordered_reasons = dict(sorted(reasons.items()))
    funnel_counts, funnel_percentages = _ordered_funnel(
        evaluated,
        actionable,
        ordered_reasons,
    )
    return StrategyDiagnostics(
        bars_available=len(bars),
        bars_evaluated=evaluated,
        actionable_signals=actionable,
        buy_signals=buys,
        sell_signals=sells,
        signal_frequency_percent=frequency,
        reason_counts=ordered_reasons,
        funnel_counts=funnel_counts,
        funnel_percentages=funnel_percentages,
    )

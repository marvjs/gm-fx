"""Compose regime, strategy selection, and higher-timeframe confirmation."""

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.predictions.config import PredictionSettings
from grandmaster_fx.predictions.confirmation import confirm_higher_timeframe
from grandmaster_fx.predictions.models import PredictionAssessment
from grandmaster_fx.predictions.regime import classify_regime
from grandmaster_fx.strategies.models import Signal


class PredictionEngine:
    def __init__(self, settings: PredictionSettings) -> None:
        self.settings = settings

    def assess(
        self, strategy_id: str, signal: Signal, primary_bars: list[Bar], higher_bars: list[Bar]
    ) -> PredictionAssessment:
        regime = classify_regime(primary_bars, self.settings.regime)
        allowed = strategy_id in self.settings.selection.strategies_for(regime.regime)
        confirmation = confirm_higher_timeframe(
            signal, higher_bars, regime.regime, self.settings.confirmation
        )
        return PredictionAssessment(strategy_id, allowed, signal, regime, confirmation)

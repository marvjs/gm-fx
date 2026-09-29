"""Adapters that expose existing strategies through the research protocol."""

from dataclasses import dataclass
from pathlib import Path

from grandmaster_fx.config.strategy import StrategySettings, load_strategy_settings
from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.baseline import evaluate_baseline
from grandmaster_fx.strategies.models import StrategyDecision


@dataclass(frozen=True, slots=True)
class BaselineStrategyAdapter:
    """Expose the baseline scalper through ResearchStrategy."""

    settings: StrategySettings

    @property
    def identifier(self) -> str:
        return "baseline_scalper"

    @property
    def minimum_bars(self) -> int:
        return self.settings.strategy.minimum_bars

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        return evaluate_baseline(symbol, bars, point, self.settings)


def load_baseline_adapter(path: Path) -> BaselineStrategyAdapter:
    """Load the existing baseline settings through a manifest path."""
    return BaselineStrategyAdapter(load_strategy_settings(path))

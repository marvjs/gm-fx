"""Common protocol for research strategy implementations."""

from typing import Protocol, runtime_checkable

from grandmaster_fx.domain.market_data import Bar
from grandmaster_fx.strategies.models import StrategyDecision


class ResearchStrategy(Protocol):
    """Evaluate completed candles without creating or submitting an order."""

    @property
    def identifier(self) -> str:
        """Return the stable strategy identifier."""
        ...

    @property
    def minimum_bars(self) -> int:
        """Return the minimum completed history requirement."""
        ...

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        """Return an immutable research decision."""
        ...


@runtime_checkable
class IndexedResearchStrategy(Protocol):
    """Optional high-performance strategy interface for historical simulation."""

    def prepare(self, bars: list[Bar]) -> object:
        """Precompute immutable indicators for one candle set."""
        ...

    def evaluate_at(
        self, symbol: str, bars: list[Bar], index: int, point: float, context: object
    ) -> StrategyDecision:
        """Evaluate one completed candle by index."""
        ...

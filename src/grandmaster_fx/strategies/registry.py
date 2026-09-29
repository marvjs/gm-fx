"""Strategy registry and manifest-driven construction."""

from collections.abc import Callable

from grandmaster_fx.config.experiments import StrategyKind, StrategyManifest
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.strategies.protocol import ResearchStrategy

StrategyFactory = Callable[[StrategyManifest], ResearchStrategy]


class StrategyRegistry:
    """Construct registered research strategies by explicit kind."""

    def __init__(self) -> None:
        self._factories: dict[StrategyKind, StrategyFactory] = {}

    def register(self, kind: StrategyKind, factory: StrategyFactory) -> None:
        """Register one factory and reject accidental replacement."""
        if kind in self._factories:
            message = f"Strategy kind is already registered: {kind}"
            raise ConfigurationError(message)
        self._factories[kind] = factory

    def create(self, manifest: StrategyManifest) -> ResearchStrategy:
        """Build one enabled strategy from its manifest."""
        factory = self._factories.get(manifest.kind)
        if factory is None:
            message = f"Strategy kind is not registered: {manifest.kind}"
            raise ConfigurationError(message)
        return factory(manifest)

    @property
    def kinds(self) -> tuple[str, ...]:
        """Return registered kinds in stable order."""
        return tuple(sorted(self._factories))

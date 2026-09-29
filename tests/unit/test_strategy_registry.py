"""Strategy registry tests."""

from pathlib import Path

import pytest

from grandmaster_fx.config.experiments import StrategyManifest
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.strategies.registry import StrategyRegistry


def manifest() -> StrategyManifest:
    return StrategyManifest(
        id="baseline_scalper",
        kind="baseline",
        enabled=True,
        config=Path("strategy.toml"),
    )


def test_registry_creates_registered_strategy() -> None:
    registry = StrategyRegistry()
    value = object()
    registry.register("baseline", lambda _manifest: value)  # type: ignore[arg-type, return-value]
    assert registry.create(manifest()) is value
    assert registry.kinds == ("baseline",)


def test_registry_rejects_duplicate_kind() -> None:
    registry = StrategyRegistry()
    registry.register("baseline", lambda _manifest: object())  # type: ignore[arg-type, return-value]
    with pytest.raises(ConfigurationError, match="already registered"):
        registry.register("baseline", lambda _manifest: object())  # type: ignore[arg-type, return-value]


def test_registry_rejects_unregistered_kind() -> None:
    registry = StrategyRegistry()
    with pytest.raises(ConfigurationError, match="not registered"):
        registry.create(manifest())

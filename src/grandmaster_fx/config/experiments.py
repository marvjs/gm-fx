"""Validated strategy experiment configuration."""

import tomllib
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from grandmaster_fx.exceptions import ConfigurationError

DEFAULT_EXPERIMENT_PATH = Path("configs/experiments.toml")
StrategyKind = Literal[
    "baseline",
    "donchian_breakout",
    "volatility_expansion",
    "volatility_expansion_window",
    "session_range_breakout",
    "fibonacci_pullback",
    "channel_mean_reversion",
    "momentum_continuation",
    "extreme_mean_reversion",
]


class ExperimentThresholds(BaseModel):
    """Shared acceptance thresholds for strategy comparisons."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    default_timeframe: str
    default_count: int = Field(gt=100)
    minimum_trades: int = Field(gt=0)
    minimum_profit_factor: float = Field(gt=0)
    minimum_expectancy: float
    maximum_drawdown_percent: float = Field(gt=0)
    minimum_profitable_fold_percent: float = Field(ge=0, le=100)
    minimum_signal_frequency_percent: float = Field(default=0.10, ge=0, le=100)


class ExecutionEligibility(BaseModel):
    """Hard research gates that remain separate from broker execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    require_holdout_pass: bool = True
    require_walk_forward_stability: bool = True
    require_all_cost_scenarios_nonnegative: bool = True
    execution_enabled: bool = False


class StrategyManifest(BaseModel):
    """One reproducible strategy experiment declaration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(min_length=1, pattern=r"^[a-z][a-z0-9_]*$")
    kind: StrategyKind
    enabled: bool = True
    config: Path


class ExperimentSettings(BaseModel):
    """Root experiment manifest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    experiments: ExperimentThresholds
    eligibility: ExecutionEligibility
    strategies: tuple[StrategyManifest, ...] = Field(min_length=1)


def load_experiment_settings(
    path: Path = DEFAULT_EXPERIMENT_PATH,
) -> ExperimentSettings:
    """Load and validate the experiment manifest."""
    try:
        with path.open("rb") as stream:
            settings = ExperimentSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Experiment configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error
    identifiers = [item.id for item in settings.strategies]
    if len(set(identifiers)) != len(identifiers):
        message = "Experiment strategy identifiers must be unique"
        raise ConfigurationError(message)
    return settings

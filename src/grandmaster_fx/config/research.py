"""Validated strategy research configuration."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grandmaster_fx.exceptions import ConfigurationError

DEFAULT_RESEARCH_PATH = Path("configs/research.toml")


class ValidationThresholds(BaseModel):
    """Minimum out-of-sample requirements for research acceptance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    in_sample_fraction: float = Field(gt=0.5, lt=0.9)
    minimum_trades: int = Field(gt=0)
    minimum_profit_factor: float = Field(gt=0)
    minimum_expectancy: float
    maximum_drawdown_percent: float = Field(gt=0)
    minimum_out_of_sample_return_percent: float


class SensitivitySettings(BaseModel):
    """Cost assumptions evaluated by sensitivity analysis."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    spread_multipliers: tuple[float, ...] = Field(min_length=1)
    slippage_points: tuple[float, ...] = Field(min_length=1)
    commission_per_lot: tuple[float, ...] = Field(min_length=1)


class WalkForwardSettings(BaseModel):
    """Anchored walk-forward window requirements."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    folds: int = Field(ge=2, le=12)
    minimum_train_bars: int = Field(gt=0)
    minimum_test_bars: int = Field(gt=0)


class ResearchExports(BaseModel):
    """Research artifact output settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    directory: Path


class ResearchSettings(BaseModel):
    """Root strategy research configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    validation: ValidationThresholds
    sensitivity: SensitivitySettings
    walk_forward: WalkForwardSettings
    exports: ResearchExports


def load_research_settings(path: Path = DEFAULT_RESEARCH_PATH) -> ResearchSettings:
    """Load and validate strategy research settings."""
    try:
        with path.open("rb") as stream:
            return ResearchSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Research configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error

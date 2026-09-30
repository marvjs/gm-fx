"""Prediction-phase configuration."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.exceptions import ConfigurationError
from grandmaster_fx.predictions.models import MarketRegime


class RegimeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    fast_period: int = Field(gt=1)
    slow_period: int = Field(gt=2)
    atr_period: int = Field(gt=1)
    volatility_lookback: int = Field(gt=2)
    trend_strength_threshold: float = Field(gt=0)
    compression_ratio_threshold: float = Field(gt=0, lt=1)
    high_volatility_ratio_threshold: float = Field(gt=1)
    minimum_efficiency_ratio: float = Field(ge=0, le=1)


class SelectionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    trend: tuple[str, ...]
    range: tuple[str, ...]
    compression: tuple[str, ...]
    high_volatility: tuple[str, ...]
    uncertain: tuple[str, ...]

    def strategies_for(self, regime: MarketRegime) -> tuple[str, ...]:
        mapping = {
            MarketRegime.TREND: self.trend,
            MarketRegime.RANGE: self.range,
            MarketRegime.COMPRESSION: self.compression,
            MarketRegime.HIGH_VOLATILITY: self.high_volatility,
            MarketRegime.UNCERTAIN: self.uncertain,
        }
        return mapping[regime]


class ConfirmationSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    enabled: bool = True
    higher_timeframe: Timeframe
    fast_period: int = Field(gt=1)
    slow_period: int = Field(gt=2)
    minimum_momentum_percent: float = Field(ge=0)
    require_regime_alignment: bool = True


class PredictionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    regime: RegimeSettings
    selection: SelectionSettings
    confirmation: ConfirmationSettings

    @model_validator(mode="after")
    def validate_periods(self) -> "PredictionSettings":
        if self.regime.fast_period >= self.regime.slow_period:
            message = "regime fast period must be below slow period"
            raise ValueError(message)
        if self.confirmation.fast_period >= self.confirmation.slow_period:
            message = "confirmation fast period must be below slow period"
            raise ValueError(message)
        return self


def load_prediction_settings(
    path: Path = Path("configs/predictions.toml"),
) -> PredictionSettings:
    try:
        with path.open("rb") as stream:
            return PredictionSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Prediction configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error

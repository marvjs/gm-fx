"""Validated paper worker configuration."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.exceptions import ConfigurationError


class WorkerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    timeframe: Timeframe
    history_bars: int = Field(ge=50)
    poll_interval_seconds: float = Field(gt=0)
    maximum_positions: int = Field(gt=0)
    minimum_score: float = Field(ge=0, le=1)
    cooldown_seconds: int = Field(ge=0)


class PaperSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    initial_balance: float = Field(gt=0)
    cash_per_point: float = Field(gt=0)
    small_profit_cash: float = Field(gt=0)
    trailing_activation_cash: float = Field(gt=0)
    trailing_retracement_cash: float = Field(gt=0)
    stop_loss_cash: float = Field(gt=0)


class SignalSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    fast_period: int = Field(gt=1)
    slow_period: int = Field(gt=2)
    momentum_period: int = Field(gt=1)
    minimum_momentum_percent: float = Field(gt=0)
    stop_atr_multiple: float = Field(gt=0)
    target_atr_multiple: float = Field(gt=0)


class PaperWorkerSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    worker: WorkerSettings
    paper: PaperSettings
    signal: SignalSettings

    @model_validator(mode="after")
    def validate_periods(self) -> "PaperWorkerSettings":
        if self.signal.fast_period >= self.signal.slow_period:
            message = "fast period must be below slow period"
            raise ValueError(message)
        if self.paper.trailing_retracement_cash >= self.paper.trailing_activation_cash:
            message = "trailing retracement must be below activation"
            raise ValueError(message)
        return self


def load_paper_worker_settings(
    path: Path = Path("configs/paper_worker.toml"),
) -> PaperWorkerSettings:
    try:
        with path.open("rb") as stream:
            return PaperWorkerSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Paper worker configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error

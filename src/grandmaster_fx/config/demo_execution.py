"""Validated demo execution settings."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grandmaster_fx.exceptions import ConfigurationError

DEFAULT_DEMO_EXECUTION_PATH = Path("configs/demo_execution.toml")


class ExecutionSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    enabled: bool = False
    dry_run: bool = True
    magic: int = Field(gt=0)
    comment: str = Field(min_length=1, max_length=31)
    deviation_points: int = Field(ge=0)
    poll_interval_seconds: float = Field(gt=0)
    cooldown_seconds: int = Field(ge=0)


class ProfitSection(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    small_profit_cash: float = Field(gt=0)
    trailing_activation_cash: float = Field(gt=0)
    trailing_retracement_cash: float = Field(gt=0)


class DemoExecutionSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    execution: ExecutionSection
    profit: ProfitSection

    @model_validator(mode="after")
    def validate_trailing(self) -> "DemoExecutionSettings":
        if self.profit.trailing_retracement_cash >= self.profit.trailing_activation_cash:
            message = "trailing retracement must be below activation"
            raise ValueError(message)
        return self


def load_demo_execution_settings(path: Path = DEFAULT_DEMO_EXECUTION_PATH) -> DemoExecutionSettings:
    try:
        with path.open("rb") as stream:
            return DemoExecutionSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Demo execution configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error

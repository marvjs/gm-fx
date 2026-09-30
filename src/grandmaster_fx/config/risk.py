"""Validated dynamic risk engine configuration."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grandmaster_fx.exceptions import ConfigurationError

DEFAULT_RISK_PATH = Path("configs/risk.toml")


class RiskParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    risk_per_trade_percent: float = Field(gt=0, le=10)
    maximum_daily_loss_percent: float = Field(gt=0, le=100)
    maximum_floating_loss_percent: float = Field(gt=0, le=100)
    maximum_open_positions: int = Field(gt=0)


class RiskSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    risk: RiskParameters


def load_risk_settings(path: Path = DEFAULT_RISK_PATH) -> RiskSettings:
    try:
        with path.open("rb") as stream:
            return RiskSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Risk configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error

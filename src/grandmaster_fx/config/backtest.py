"""Validated backtest configuration."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grandmaster_fx.exceptions import ConfigurationError

DEFAULT_BACKTEST_PATH = Path("configs/backtest.toml")


class BacktestParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    initial_balance: float = Field(gt=0)
    risk_per_trade_percent: float = Field(gt=0, le=5)
    commission_per_lot_round_turn: float = Field(ge=0)
    slippage_points: float = Field(ge=0)
    maximum_holding_bars: int = Field(gt=0)
    minimum_history_bars: int = Field(gt=2)
    conservative_same_bar_exit: bool = True


class DataQualityParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    maximum_gap_multiple: int = Field(ge=1)
    reject_history_gaps: bool = False
    maximum_data_age_hours: int = Field(gt=0)


class BacktestSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    backtest: BacktestParameters
    quality: DataQualityParameters


def load_backtest_settings(path: Path = DEFAULT_BACKTEST_PATH) -> BacktestSettings:
    try:
        with path.open("rb") as stream:
            return BacktestSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Backtest configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error

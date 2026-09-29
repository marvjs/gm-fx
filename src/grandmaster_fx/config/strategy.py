"""Validated baseline strategy configuration."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grandmaster_fx.exceptions import ConfigurationError

DEFAULT_STRATEGY_PATH = Path("configs/strategies/scalp_baseline.toml")


class StrategyParameters(BaseModel):
    """Indicator periods and history requirements."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    enabled: bool = True
    fast_ema_period: int = Field(gt=1)
    slow_ema_period: int = Field(gt=2)
    rsi_period: int = Field(gt=1)
    atr_period: int = Field(gt=1)
    roc_period: int = Field(gt=0)
    minimum_bars: int = Field(gt=2)

    @model_validator(mode="after")
    def validate_periods(self) -> "StrategyParameters":
        """Ensure the slow trend period exceeds the fast trend period."""
        if self.slow_ema_period <= self.fast_ema_period:
            message = "slow_ema_period must exceed fast_ema_period"
            raise ValueError(message)
        required = max(
            self.slow_ema_period,
            self.rsi_period + 1,
            self.atr_period,
            self.roc_period + 1,
        )
        if self.minimum_bars < required:
            message = "minimum_bars must cover every configured indicator period"
            raise ValueError(message)
        return self


class StrategyFilters(BaseModel):
    """Spread, volatility, momentum, and session filters."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    max_spread_points: int = Field(ge=0)
    minimum_atr_points: float = Field(gt=0)
    maximum_atr_points: float = Field(gt=0)
    minimum_roc_percent: float = Field(ge=0)
    buy_rsi_min: float = Field(ge=0, le=100)
    buy_rsi_max: float = Field(ge=0, le=100)
    sell_rsi_min: float = Field(ge=0, le=100)
    sell_rsi_max: float = Field(ge=0, le=100)
    session_start_utc: int = Field(ge=0, le=23)
    session_end_utc: int = Field(ge=1, le=24)

    @model_validator(mode="after")
    def validate_ranges(self) -> "StrategyFilters":
        """Validate ordered filter ranges."""
        if self.maximum_atr_points <= self.minimum_atr_points:
            message = "maximum_atr_points must exceed minimum_atr_points"
            raise ValueError(message)
        if self.buy_rsi_max <= self.buy_rsi_min:
            message = "buy RSI maximum must exceed its minimum"
            raise ValueError(message)
        if self.sell_rsi_max <= self.sell_rsi_min:
            message = "sell RSI maximum must exceed its minimum"
            raise ValueError(message)
        if self.session_end_utc <= self.session_start_utc:
            message = "session_end_utc must exceed session_start_utc"
            raise ValueError(message)
        return self


class ProtectionParameters(BaseModel):
    """ATR-derived protective-price configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stop_atr_multiple: float = Field(gt=0)
    target_atr_multiple: float = Field(gt=0)
    minimum_reward_risk: float = Field(gt=0)

    @model_validator(mode="after")
    def validate_reward_risk(self) -> "ProtectionParameters":
        """Reject protection settings below the minimum reward-risk ratio."""
        ratio = self.target_atr_multiple / self.stop_atr_multiple
        if ratio < self.minimum_reward_risk:
            message = "configured ATR protection does not meet minimum_reward_risk"
            raise ValueError(message)
        return self


class StrategySettings(BaseModel):
    """Root baseline strategy settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    strategy: StrategyParameters
    filters: StrategyFilters
    protection: ProtectionParameters


def load_strategy_settings(path: Path = DEFAULT_STRATEGY_PATH) -> StrategySettings:
    """Load and validate baseline strategy settings."""
    try:
        with path.open("rb") as stream:
            return StrategySettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Strategy configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error

"""Validated application configuration models."""

from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator

from grandmaster_fx.exceptions import SafetyViolationError


class Environment(StrEnum):
    """Supported runtime environments."""

    DEVELOPMENT = "development"
    TEST = "test"
    PRODUCTION = "production"


class ExecutionMode(StrEnum):
    """Execution modes, with observe as the safe default."""

    OBSERVE = "observe"
    DEMO = "demo"


class AppSection(BaseModel):
    """General application settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(min_length=1)
    environment: Environment = Environment.DEVELOPMENT
    log_level: str = Field(default="INFO", pattern=r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$")
    log_directory: Path = Path("logs")
    data_directory: Path = Path("data")


class ExecutionSection(BaseModel):
    """Execution safety settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    mode: ExecutionMode = ExecutionMode.OBSERVE
    allow_live_account: bool = False

    @model_validator(mode="after")
    def reject_live_trading(self) -> "ExecutionSection":
        """Block live trading throughout the staged build."""
        if self.allow_live_account:
            message = "Live-account execution is prohibited. Set allow_live_account to false."
            raise SafetyViolationError(message)
        return self


class AppSettings(BaseModel):
    """Root settings object loaded from the application TOML file."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    app: AppSection
    execution: ExecutionSection

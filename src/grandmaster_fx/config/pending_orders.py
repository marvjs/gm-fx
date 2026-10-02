"""Validated shared pending-order configuration."""

import tomllib
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from grandmaster_fx.exceptions import ConfigurationError

DEFAULT_PENDING_ORDER_PATH = Path("configs/pending_orders.toml")


class ReplacementPolicy(StrEnum):
    """How a newer equivalent plan interacts with an active order."""

    RETAIN_EXISTING = "retain_existing"
    CANCEL_AND_REPLACE = "cancel_and_replace"


class PendingOrderParameters(BaseModel):
    """Shared planning rules used by every execution profile."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    enabled: bool = True
    trigger_offset_atr: float = Field(gt=0, le=2)
    maximum_wait_bars: int = Field(gt=0, le=100)
    replacement_policy: ReplacementPolicy = ReplacementPolicy.RETAIN_EXISTING
    allow_market: bool = False
    allow_stop: bool = True
    allow_limit: bool = False


class PendingOrderSettings(BaseModel):
    """Root pending-order settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    pending: PendingOrderParameters


def load_pending_order_settings(
    path: Path = DEFAULT_PENDING_ORDER_PATH,
) -> PendingOrderSettings:
    """Load and validate shared pending-order settings."""
    try:
        with path.open("rb") as stream:
            return PendingOrderSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        message = f"Pending-order configuration is invalid: {path}: {error}"
        raise ConfigurationError(message) from error

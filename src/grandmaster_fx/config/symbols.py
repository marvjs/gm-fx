"""Versioned forex symbol configuration."""

import tomllib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, field_validator

from grandmaster_fx.exceptions import ConfigurationError

DEFAULT_SYMBOLS_PATH = Path("configs/symbols.toml")


class SymbolSection(BaseModel):
    """Currency universe and preferred normalized pairs."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    allowed_currencies: frozenset[str] = Field(min_length=2)
    preferred: tuple[str, ...]
    include_hidden: bool = True

    @field_validator("allowed_currencies")
    @classmethod
    def validate_currencies(cls, values: frozenset[str]) -> frozenset[str]:
        if any(len(item) != 3 or not item.isalpha() or not item.isupper() for item in values):
            raise ValueError("currency codes must be uppercase three-letter codes")
        return values

    @field_validator("preferred")
    @classmethod
    def validate_pairs(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any(len(item) != 6 or not item.isalpha() or not item.isupper() for item in values):
            raise ValueError("preferred pairs must be uppercase six-letter codes")
        return values


class SymbolValidation(BaseModel):
    """Metadata requirements for eligible forex symbols."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    require_trade_enabled: bool = True
    require_positive_tick_size: bool = True
    require_positive_volume_step: bool = True


class SymbolSettings(BaseModel):
    """Root symbol settings."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    symbols: SymbolSection
    validation: SymbolValidation


def load_symbol_settings(path: Path = DEFAULT_SYMBOLS_PATH) -> SymbolSettings:
    """Load symbol settings from TOML."""
    try:
        with path.open("rb") as stream:
            return SymbolSettings.model_validate(tomllib.load(stream))
    except (OSError, tomllib.TOMLDecodeError, ValueError) as error:
        raise ConfigurationError(f"Symbol configuration is invalid: {path}: {error}") from error

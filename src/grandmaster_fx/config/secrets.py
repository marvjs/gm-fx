"""Private, environment-backed MT5 connection settings."""

from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from grandmaster_fx.exceptions import ConfigurationError


class Mt5Secrets(BaseSettings):
    """Credentials and machine-specific terminal path loaded from environment."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    mt5_login: int | None = None
    mt5_password: str | None = None
    mt5_server: str | None = None
    mt5_terminal_path: Path | None = None
    mt5_timeout_ms: int = 60_000

    @model_validator(mode="after")
    def credentials_are_complete(self) -> "Mt5Secrets":
        """Allow terminal-session reuse or a complete credential triplet, never partial secrets."""
        supplied = (self.mt5_login, self.mt5_password, self.mt5_server)
        if any(value is not None for value in supplied) and not all(
            value is not None for value in supplied
        ):
            message = (
                "MT5 credentials are incomplete. Set MT5_LOGIN, MT5_PASSWORD, and "
                "MT5_SERVER together, or leave all three unset to reuse the terminal session."
            )
            raise ConfigurationError(message)
        return self

    @property
    def has_credentials(self) -> bool:
        """Return whether a complete explicit credential set is available."""
        return self.mt5_login is not None

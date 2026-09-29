"""Application-specific exception hierarchy."""


class GrandmasterFxError(Exception):
    """Base exception for expected application failures."""


class ConfigurationError(GrandmasterFxError):
    """Raised when application configuration is missing or invalid."""


class SafetyViolationError(GrandmasterFxError):
    """Raised when a requested action violates a safety invariant."""


class Mt5Error(GrandmasterFxError):
    """Base exception for MetaTrader 5 integration failures."""


class Mt5PackageUnavailableError(Mt5Error):
    """Raised when the official MetaTrader 5 Python package cannot be imported."""


class Mt5ConnectionError(Mt5Error):
    """Raised when the terminal cannot be initialized or authenticated."""


class Mt5DataError(Mt5Error):
    """Raised when terminal or account information is unavailable."""

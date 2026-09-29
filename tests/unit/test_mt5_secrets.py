"""MT5 secret configuration tests."""

import pytest

from grandmaster_fx.config import Mt5Secrets
from grandmaster_fx.exceptions import ConfigurationError


def test_empty_credentials_reuse_terminal_session() -> None:
    secrets = Mt5Secrets(_env_file=None)
    assert not secrets.has_credentials


def test_complete_credentials_are_accepted() -> None:
    secrets = Mt5Secrets(
        mt5_login=123, mt5_password="secret", mt5_server="Broker-Demo", _env_file=None
    )
    assert secrets.has_credentials


def test_partial_credentials_are_rejected() -> None:
    with pytest.raises(ConfigurationError, match="incomplete"):
        Mt5Secrets(mt5_login=123, _env_file=None)

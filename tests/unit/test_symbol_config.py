"""Symbol configuration tests."""

from pathlib import Path

import pytest

from grandmaster_fx.config.symbols import load_symbol_settings
from grandmaster_fx.exceptions import ConfigurationError


def test_load_symbol_settings(tmp_path: Path) -> None:
    path = tmp_path / "symbols.toml"
    path.write_text(
        '[symbols]\nallowed_currencies=["EUR","USD"]\npreferred=["EURUSD"]\ninclude_hidden=true\n[validation]\nrequire_trade_enabled=true\nrequire_positive_tick_size=true\nrequire_positive_volume_step=true\n'
    )
    assert load_symbol_settings(path).symbols.preferred == ("EURUSD",)


def test_invalid_currency_rejected(tmp_path: Path) -> None:
    path = tmp_path / "symbols.toml"
    path.write_text(
        '[symbols]\nallowed_currencies=["euro","USD"]\npreferred=["EURUSD"]\n[validation]\n'
    )
    with pytest.raises(ConfigurationError):
        load_symbol_settings(path)

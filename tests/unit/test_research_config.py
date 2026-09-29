"""Research configuration tests."""

from pathlib import Path

import pytest

from grandmaster_fx.config.research import load_research_settings
from grandmaster_fx.exceptions import ConfigurationError


def test_default_research_configuration_loads() -> None:
    assert load_research_settings().walk_forward.folds == 4


def test_missing_research_configuration_is_wrapped(tmp_path: Path) -> None:
    with pytest.raises(ConfigurationError, match="invalid"):
        load_research_settings(tmp_path / "missing.toml")

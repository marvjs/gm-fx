"""Health-check tests."""

from pathlib import Path

from grandmaster_fx.application.doctor import run_health_checks
from grandmaster_fx.config import load_settings


def test_health_checks_pass_for_valid_foundation(
    tmp_path: Path,
    valid_config_text: str,
) -> None:
    config_path = tmp_path / "app.toml"
    config_path.write_text(valid_config_text, encoding="utf-8")
    settings = load_settings(config_path)

    results = run_health_checks(settings, config_path)

    assert results
    assert all(result.ok for result in results)
    assert settings.app.log_directory.is_dir()
    assert settings.app.data_directory.is_dir()

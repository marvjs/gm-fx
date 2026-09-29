"""Command-line tests."""

from pathlib import Path

from typer.testing import CliRunner

from grandmaster_fx import __version__
from grandmaster_fx.cli import app

runner = CliRunner()


def test_version() -> None:
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_doctor_passes_with_valid_config(tmp_path: Path, valid_config_text: str) -> None:
    config_path = tmp_path / "app.toml"
    config_path.write_text(valid_config_text, encoding="utf-8")

    result = runner.invoke(app, ["doctor", "--config", str(config_path)])

    assert result.exit_code == 0
    assert "Foundation is healthy" in result.stdout
    assert "PASS" in result.stdout


def test_show_config_excludes_secrets(tmp_path: Path, valid_config_text: str) -> None:
    config_path = tmp_path / "app.toml"
    config_path.write_text(valid_config_text, encoding="utf-8")

    result = runner.invoke(app, ["show-config", "--config", str(config_path)])

    assert result.exit_code == 0
    assert '"mode": "observe"' in result.stdout
    assert "password" not in result.stdout.lower()

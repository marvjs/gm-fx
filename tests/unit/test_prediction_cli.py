"""Prediction CLI command-surface tests."""

from typer.testing import CliRunner

from grandmaster_fx.cli import app

runner = CliRunner()


def test_predictions_help() -> None:
    result = runner.invoke(app, ["predictions", "--help"])
    assert result.exit_code == 0
    assert "inspect" in result.stdout
    assert "config" in result.stdout


def test_predictions_inspect_help() -> None:
    result = runner.invoke(app, ["predictions", "inspect", "--help"])
    assert result.exit_code == 0
    assert "--timeframe" in result.stdout
    assert "--strategy" in result.stdout

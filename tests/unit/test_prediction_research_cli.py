"""Prediction-aware research CLI surface tests."""

from typer.testing import CliRunner

from grandmaster_fx.cli import app

runner = CliRunner()


def test_research_validate_exposes_strategy_and_prediction_options() -> None:
    result = runner.invoke(app, ["research", "validate", "--help"])
    assert result.exit_code == 0
    assert "--strategy" in result.stdout
    assert "--predictions" in result.stdout
    assert "--no-predictions" in result.stdout


def test_research_robustness_exposes_strategy_and_prediction_options() -> None:
    result = runner.invoke(app, ["research", "robustness", "--help"])
    assert result.exit_code == 0
    assert "--strategy" in result.stdout
    assert "--predictions" in result.stdout
    assert "--no-predictions" in result.stdout

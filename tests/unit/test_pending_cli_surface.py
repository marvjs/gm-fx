"""Pending integration CLI surface tests."""

from typer.testing import CliRunner

from grandmaster_fx.cli import app

runner = CliRunner()


def test_pending_inspect_help_keeps_explicit_controls() -> None:
    result = runner.invoke(app, ["pending", "inspect", "--help"])
    assert result.exit_code == 0
    assert "--strategy" in result.stdout
    assert "--timeframe" in result.stdout
    assert "--direction" in result.stdout
    assert "--predictions" in result.stdout


def test_paper_pending_commands_are_registered() -> None:
    result = runner.invoke(app, ["paper", "--help"])
    assert result.exit_code == 0
    assert "pending-place" in result.stdout
    assert "pending-list" in result.stdout
    assert "pending-reconcile" in result.stdout

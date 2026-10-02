"""Live pending command-surface tests."""

from typer.testing import CliRunner

from grandmaster_fx.cli import app

runner = CliRunner()


def test_live_pending_commands_are_registered() -> None:
    result = runner.invoke(app, ["live", "--help"])
    assert result.exit_code == 0
    for command in ("pending-place", "pending-list", "pending-reconcile", "pending-cancel"):
        assert command in result.stdout

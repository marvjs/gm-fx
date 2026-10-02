from typer.testing import CliRunner

from grandmaster_fx.cli import app

runner = CliRunner()


def test_pending_backtest_registered() -> None:
    result = runner.invoke(app, ["pending", "--help"])
    assert result.exit_code == 0
    assert "backtest" in result.stdout


def test_demo_pending_commands_registered() -> None:
    result = runner.invoke(app, ["demo", "--help"])
    assert result.exit_code == 0
    for name in ("pending-place", "pending-list", "pending-reconcile", "pending-cancel"):
        assert name in result.stdout

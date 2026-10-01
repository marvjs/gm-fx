"""Live CLI Typer tests."""

from unittest.mock import Mock, patch

from typer.testing import CliRunner

from grandmaster_fx.cli import app

runner = CliRunner()


@patch("grandmaster_fx.cli._create_worker")
def test_live_status_command(mock_worker: Mock) -> None:
    gateway = Mock()
    worker = Mock()
    worker.status.return_value = {"balance": 1000.0}
    mock_worker.return_value = (gateway, worker)

    result = runner.invoke(app, ["live", "status"])
    assert result.exit_code == 0
    assert "1000" in result.stdout
    gateway.close.assert_called_once()


@patch("grandmaster_fx.cli._create_worker")
def test_live_cycle_command(mock_worker: Mock) -> None:
    gateway = Mock()
    worker = Mock()
    worker.cycle.return_value = {"opened": ["EURUSDm"]}
    mock_worker.return_value = (gateway, worker)

    result = runner.invoke(app, ["live", "cycle"])
    assert result.exit_code == 0
    assert "EURUSDm" in result.stdout
    gateway.close.assert_called_once()


@patch("grandmaster_fx.cli._create_worker")
def test_live_run_command(mock_worker: Mock) -> None:
    gateway = Mock()
    worker = Mock()
    mock_worker.return_value = (gateway, worker)

    result = runner.invoke(app, ["live", "run", "--maximum-cycles", "1"])
    assert result.exit_code == 0
    worker.run.assert_called_once_with(1)
    gateway.close.assert_called_once()


@patch("grandmaster_fx.cli._create_worker")
def test_live_dashboard_command(mock_worker: Mock) -> None:
    gateway = Mock()
    worker = Mock()
    mock_worker.return_value = (gateway, worker)

    result = runner.invoke(app, ["live", "dashboard", "--maximum-cycles", "1"])
    assert result.exit_code == 0
    worker.run_dashboard.assert_called_once_with(
        "baseline_scalper", 1, title="Grandmaster FX Live Dashboard"
    )
    gateway.close.assert_called_once()


def test_live_stop_command() -> None:
    result = runner.invoke(app, ["live", "stop"])
    assert result.exit_code == 0
    assert "stop requested" in result.stdout

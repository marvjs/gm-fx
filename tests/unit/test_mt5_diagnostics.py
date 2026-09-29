"""MT5 diagnostic orchestration tests."""

from unittest.mock import Mock

from grandmaster_fx.application.mt5_diagnostics import inspect_connection


def test_inspect_connection_collects_all_snapshots() -> None:
    gateway = Mock()
    gateway.version.return_value = (5, 0, "6231")
    gateway.terminal.return_value = Mock()
    gateway.account.return_value = Mock()
    report = inspect_connection(gateway)
    assert report.package_version == (5, 0, "6231")
    gateway.terminal.assert_called_once()
    gateway.account.assert_called_once()

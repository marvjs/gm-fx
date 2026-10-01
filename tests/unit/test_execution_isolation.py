"""Operational isolation for demo and live execution profiles."""

import pytest

from grandmaster_fx.config.execution_profile import ExecutionProfile, load_execution_runtime
from grandmaster_fx.config.models import AppSection, AppSettings, ExecutionMode, ExecutionSection
from grandmaster_fx.domain.mt5 import AccountSnapshot, AccountTradeMode
from grandmaster_fx.exceptions import ConfigurationError, SafetyViolationError


def app(mode: ExecutionMode, *, live: bool = False) -> AppSettings:
    return AppSettings(
        app=AppSection(name="Grandmaster FX"),
        execution=ExecutionSection(mode=mode, allow_live_account=live),
    )


def account(mode: AccountTradeMode) -> AccountSnapshot:
    return AccountSnapshot(
        1, mode, "server", "company", "USD", 100, 1000, 1000, 0, 1000, 0, True, True
    )


def test_demo_and_live_paths_are_disjoint() -> None:
    demo = load_execution_runtime(ExecutionProfile.DEMO, app(ExecutionMode.DEMO))
    live = load_execution_runtime(ExecutionProfile.LIVE, app(ExecutionMode.LIVE, live=True))
    assert demo.stop_path != live.stop_path
    assert demo.consumed_path != live.consumed_path
    assert demo.journal_path != live.journal_path
    assert demo.settings.execution.magic != live.settings.execution.magic


def test_profile_requires_matching_application_mode() -> None:
    with pytest.raises(ConfigurationError, match=r"require execution\.mode"):
        load_execution_runtime(ExecutionProfile.DEMO, app(ExecutionMode.OBSERVE))


def test_live_profile_requires_explicit_authorization() -> None:
    with pytest.raises(SafetyViolationError, match="allow_live_account"):
        load_execution_runtime(ExecutionProfile.LIVE, app(ExecutionMode.LIVE))


def test_real_account_guard_rejects_demo_and_contest() -> None:
    with pytest.raises(SafetyViolationError):
        account(AccountTradeMode.DEMO).require_real()
    with pytest.raises(SafetyViolationError):
        account(AccountTradeMode.CONTEST).require_real()
    account(AccountTradeMode.REAL).require_real()

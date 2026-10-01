"""Validated execution profiles and isolated runtime paths."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from grandmaster_fx.config.demo_execution import (
    DemoExecutionSettings,
    load_demo_execution_settings,
)
from grandmaster_fx.config.models import AppSettings, ExecutionMode
from grandmaster_fx.exceptions import ConfigurationError, SafetyViolationError


class ExecutionProfile(StrEnum):
    DEMO = "demo"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class ExecutionRuntime:
    profile: ExecutionProfile
    settings: DemoExecutionSettings
    stop_path: Path
    consumed_path: Path
    journal_path: Path

    @property
    def label(self) -> str:
        return self.profile.value.upper()


def load_execution_runtime(
    profile: ExecutionProfile,
    app: AppSettings,
) -> ExecutionRuntime:
    if profile is ExecutionProfile.DEMO:
        settings = load_demo_execution_settings(Path("configs/demo_execution.toml"))
        required_mode = ExecutionMode.DEMO
    else:
        settings = load_demo_execution_settings(Path("configs/live_execution.toml"))
        required_mode = ExecutionMode.LIVE
        if not app.execution.allow_live_account:
            message = "Live execution requires allow_live_account = true"
            raise SafetyViolationError(message)
    if app.execution.mode is not required_mode:
        message = (
            f"{profile.value} commands require execution.mode = "
            f"'{required_mode.value}' in configs/app.toml"
        )
        raise ConfigurationError(message)
    base = Path("data/execution") / profile.value
    return ExecutionRuntime(
        profile=profile,
        settings=settings,
        stop_path=base / "STOP",
        consumed_path=base / "consumed_predictions.json",
        journal_path=base / "journal.jsonl",
    )

"""Local project health checks."""

import platform
import sys
from pathlib import Path

from grandmaster_fx.config.models import AppSettings
from grandmaster_fx.console import CheckResult


def run_health_checks(settings: AppSettings, config_path: Path) -> list[CheckResult]:
    """Run non-networked checks for the Block 1 project foundation."""
    python_ok = sys.version_info[:2] == (3, 12)
    config_ok = config_path.is_file()
    safe_mode = not settings.execution.allow_live_account

    directories: list[Path] = [settings.app.log_directory, settings.app.data_directory]
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    directories_ok = all(directory.is_dir() for directory in directories)

    return [
        CheckResult(
            name="Python",
            ok=python_ok,
            detail=f"{platform.python_version()} (required: 3.12.x)",
        ),
        CheckResult(
            name="Configuration",
            ok=config_ok,
            detail=str(config_path.resolve()),
        ),
        CheckResult(
            name="Runtime directories",
            ok=directories_ok,
            detail=", ".join(str(item.resolve()) for item in directories),
        ),
        CheckResult(
            name="Live-account guard",
            ok=safe_mode,
            detail="live execution disabled" if safe_mode else "unsafe configuration",
        ),
    ]

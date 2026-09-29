"""Experiment eligibility and identifier tests."""

from pathlib import Path

from grandmaster_fx.config.experiments import (
    ExecutionEligibility,
    ExperimentSettings,
    ExperimentThresholds,
    StrategyManifest,
)
from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.experiments.runner import evaluate_eligibility, experiment_id
from grandmaster_fx.research.robustness import StabilitySummary


def settings(*, execution_enabled: bool = False) -> ExperimentSettings:
    return ExperimentSettings(
        experiments=ExperimentThresholds(
            default_timeframe="M5",
            default_count=10000,
            minimum_trades=30,
            minimum_profit_factor=1.1,
            minimum_expectancy=0,
            maximum_drawdown_percent=15,
            minimum_profitable_fold_percent=75,
        ),
        eligibility=ExecutionEligibility(execution_enabled=execution_enabled),
        strategies=(
            StrategyManifest(
                id="baseline_scalper",
                kind="baseline",
                config=Path("strategy.toml"),
            ),
        ),
    )


def test_experiment_identifier_is_stable() -> None:
    manifest = settings().strategies[0]
    first = experiment_id(manifest, "EURUSDm", Timeframe.M5)
    assert first == experiment_id(manifest, "EURUSDm", Timeframe.M5)
    assert first.startswith("baseline_scalper-eurusdm-m5-")


def test_global_execution_disable_is_a_hard_gate() -> None:
    stable = StabilitySummary(4, 4, 100, 100, 10, 5, 1.2, True)
    eligible, reasons = evaluate_eligibility(
        stable,
        settings(),
        holdout_passed=True,
        all_cost_scenarios_nonnegative=True,
    )
    assert not eligible
    assert reasons == ("execution_globally_disabled",)


def test_failed_research_gates_are_explicit() -> None:
    eligible, reasons = evaluate_eligibility(
        None,
        settings(),
        holdout_passed=False,
        all_cost_scenarios_nonnegative=False,
    )
    assert not eligible
    assert "holdout_failed" in reasons
    assert "walk_forward_unstable" in reasons
    assert "cost_sensitivity_failed" in reasons

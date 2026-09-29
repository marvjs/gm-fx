"""Experiment runner orchestration and export tests."""

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from grandmaster_fx.backtesting.models import BacktestMetrics, BacktestResult
from grandmaster_fx.config.backtest import (
    BacktestParameters,
    BacktestSettings,
    DataQualityParameters,
)
from grandmaster_fx.config.experiments import (
    ExecutionEligibility,
    ExperimentSettings,
    ExperimentThresholds,
    StrategyManifest,
)
from grandmaster_fx.config.research import (
    ResearchExports,
    ResearchSettings,
    SensitivitySettings,
    ValidationThresholds,
    WalkForwardSettings,
)
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.experiments import runner
from grandmaster_fx.experiments.diagnostics import StrategyDiagnostics
from grandmaster_fx.experiments.modes import ExperimentMode
from grandmaster_fx.experiments.runner import (
    ExperimentOutcome,
    StrategyExperimentRequest,
    _cost_scenarios_pass,
    export_outcomes,
    run_strategy_experiment,
)
from grandmaster_fx.research.models import (
    SensitivityRun,
    ValidationCheck,
    ValidationReport,
    WalkForwardFold,
)
from grandmaster_fx.research.robustness import StabilitySummary
from grandmaster_fx.strategies.models import (
    DecisionReason,
    Signal,
    StrategyDecision,
)


class Strategy:
    identifier = "test"
    minimum_bars = 3

    def evaluate(self, symbol: str, bars: list[Bar], point: float) -> StrategyDecision:
        del point
        return StrategyDecision(
            Signal.HOLD,
            symbol,
            bars[-1].time,
            None,
            None,
            None,
            None,
            (DecisionReason.TREND_NOT_ALIGNED,),
        )


def bars() -> list[Bar]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return [
        Bar(
            start + timedelta(minutes=index),
            1,
            1.1,
            0.9,
            1,
            1,
            1,
            0,
        )
        for index in range(20)
    ]


def experiment_settings() -> ExperimentSettings:
    return ExperimentSettings(
        experiments=ExperimentThresholds(
            default_timeframe="M1",
            default_count=1000,
            minimum_trades=1,
            minimum_profit_factor=1,
            minimum_expectancy=0,
            maximum_drawdown_percent=50,
            minimum_profitable_fold_percent=75,
        ),
        eligibility=ExecutionEligibility(execution_enabled=False),
        strategies=(
            StrategyManifest(
                id="test_strategy",
                kind="baseline",
                config=Path("test.toml"),
            ),
        ),
    )


def research_settings(tmp_path: Path) -> ResearchSettings:
    return ResearchSettings(
        validation=ValidationThresholds(
            in_sample_fraction=0.7,
            minimum_trades=1,
            minimum_profit_factor=1,
            minimum_expectancy=0,
            maximum_drawdown_percent=50,
            minimum_out_of_sample_return_percent=0,
        ),
        sensitivity=SensitivitySettings(
            spread_multipliers=(1.0,),
            slippage_points=(0.0,),
            commission_per_lot=(0.0,),
        ),
        walk_forward=WalkForwardSettings(
            folds=2,
            minimum_train_bars=5,
            minimum_test_bars=3,
        ),
        exports=ResearchExports(directory=tmp_path),
    )


def backtest_settings() -> BacktestSettings:
    return BacktestSettings(
        backtest=BacktestParameters(
            initial_balance=1000,
            risk_per_trade_percent=0.25,
            commission_per_lot_round_turn=0,
            slippage_points=0,
            maximum_holding_bars=2,
            minimum_history_bars=3,
            conservative_same_bar_exit=True,
        ),
        quality=DataQualityParameters(
            maximum_gap_multiple=3,
            reject_history_gaps=False,
            maximum_data_age_hours=24,
        ),
    )


def metrics(*, net: float = 0, factor: float | None = None) -> BacktestMetrics:
    return BacktestMetrics(
        1000,
        1000 + net,
        net,
        net / 10,
        0,
        1,
        int(net >= 0),
        int(net < 0),
        100 if net >= 0 else 0,
        factor,
        net,
        max(net, 0),
        abs(min(net, 0)),
        None,
        int(net < 0),
    )


def result(*, net: float = 0, factor: float | None = None) -> BacktestResult:
    return BacktestResult("EURUSDm", (), (1000, 1000 + net), metrics(net=net, factor=factor))


def request(tmp_path: Path) -> StrategyExperimentRequest:
    return StrategyExperimentRequest(
        manifest=experiment_settings().strategies[0],
        strategy=Strategy(),
        symbol="EURUSDm",
        bars=bars(),
        timeframe=Timeframe.M1,
        point=0.00001,
        contract_size=100_000,
        backtest=backtest_settings(),
        research=research_settings(tmp_path),
        experiments=experiment_settings(),
        mode=ExperimentMode.FULL,
    )


def stable_summary() -> StabilitySummary:
    return StabilitySummary(2, 2, 100, 2, 20, 1, 1.2, True)


def test_run_strategy_experiment_uses_measured_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    calls = iter((result(net=20, factor=1.2), result(net=10, factor=1.1)))
    monkeypatch.setattr(runner, "run_backtest", lambda *_args: next(calls))
    fold_result = result(net=5, factor=1.1)
    folds = (
        WalkForwardFold(1, 0, 5, 5, 8, fold_result),
        WalkForwardFold(2, 0, 8, 8, 11, fold_result),
    )
    monkeypatch.setattr(
        runner,
        "walk_forward",
        lambda *_args: (folds, stable_summary()),
    )
    scenarios = (
        SensitivityRun("slippage=0", result(net=3, factor=1.1)),
        SensitivityRun("commission=0", result(net=2, factor=1.1)),
    )
    monkeypatch.setattr(runner, "sensitivity_runs", lambda *_args: scenarios)
    monkeypatch.setattr(
        runner,
        "collect_diagnostics",
        lambda *_args: StrategyDiagnostics(
            bars_available=20,
            bars_evaluated=17,
            actionable_signals=2,
            buy_signals=1,
            sell_signals=1,
            signal_frequency_percent=11.76,
            reason_counts={"buy_setup_confirmed": 1, "sell_setup_confirmed": 1},
            funnel_counts={"bars_evaluated": 17, "actionable": 2},
            funnel_percentages={"bars_evaluated": 100.0, "actionable": 11.76},
        ),
    )
    outcome = run_strategy_experiment(request(tmp_path))
    assert outcome.full_sample.metrics.net_profit == 20
    assert outcome.holdout.metrics.net_profit == 10
    assert outcome.holdout_passed
    assert outcome.stability is not None
    assert outcome.stability.stable
    assert outcome.all_cost_scenarios_nonnegative
    assert not outcome.eligible
    assert outcome.rejection_reasons == ("execution_globally_disabled",)


def test_cost_scenarios_require_every_result_to_pass() -> None:
    passing = SensitivityRun("passing", result(net=1, factor=1.1))
    failing = SensitivityRun("failing", result(net=-1, factor=0.9))
    assert _cost_scenarios_pass((passing,))
    assert not _cost_scenarios_pass((passing, failing))
    assert not _cost_scenarios_pass(())


def test_export_outcomes_contains_complete_evidence(tmp_path: Path) -> None:
    full = result(net=20, factor=1.2)
    holdout = result(net=10, factor=1.1)
    validation = ValidationReport(
        True,
        (ValidationCheck("profit_factor", True, 1.1, 1.0),),
        (),
    )
    fold = WalkForwardFold(1, 0, 5, 5, 8, holdout)
    scenario = SensitivityRun("commission=0", holdout)
    outcome = ExperimentOutcome(
        experiment_id="experiment-1",
        strategy_id="test_strategy",
        mode=ExperimentMode.FULL,
        duration_seconds=1.25,
        stage_seconds={
            "full_sample": 0.5,
            "holdout": 0.25,
            "diagnostics": 0.5,
        },
        diagnostics=StrategyDiagnostics(
            bars_available=20,
            bars_evaluated=17,
            actionable_signals=2,
            buy_signals=1,
            sell_signals=1,
            signal_frequency_percent=11.76,
            reason_counts={
                "buy_setup_confirmed": 1,
                "sell_setup_confirmed": 1,
            },
            funnel_counts={
                "bars_evaluated": 17,
                "actionable": 2,
            },
            funnel_percentages={
                "bars_evaluated": 100.0,
                "actionable": 11.76,
            },
        ),
        full_sample=full,
        holdout=holdout,
        holdout_validation=validation,
        walk_forward_folds=(fold,),
        stability=stable_summary(),
        sensitivity=(scenario,),
        all_cost_scenarios_nonnegative=True,
        eligible=False,
        rejection_reasons=("execution_globally_disabled",),
    )
    destination = export_outcomes((outcome,), tmp_path)
    payload = json.loads(destination.read_text())[0]
    assert payload["full_sample"]["metrics"]["net_profit"] == 20
    assert payload["holdout"]["metrics"]["net_profit"] == 10
    assert payload["walk_forward"][0]["number"] == 1
    assert payload["sensitivity"][0]["label"] == "commission=0"
    assert payload["holdout_passed"] is True
    assert payload["all_cost_scenarios_nonnegative"] is True

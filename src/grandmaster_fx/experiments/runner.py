"""Reproducible multi-strategy experiment runner."""

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter

from grandmaster_fx.backtesting.engine import BacktestInput, run_backtest
from grandmaster_fx.backtesting.models import BacktestResult
from grandmaster_fx.config.backtest import BacktestSettings
from grandmaster_fx.config.experiments import ExperimentSettings, StrategyManifest
from grandmaster_fx.config.research import ResearchSettings
from grandmaster_fx.domain.market_data import Bar, Timeframe
from grandmaster_fx.experiments.diagnostics import StrategyDiagnostics, collect_diagnostics
from grandmaster_fx.experiments.modes import ExperimentMode
from grandmaster_fx.research.models import SensitivityRun, ValidationReport, WalkForwardFold
from grandmaster_fx.research.robustness import StabilitySummary, sensitivity_runs, walk_forward
from grandmaster_fx.research.splits import holdout_split
from grandmaster_fx.research.validation import validate_result
from grandmaster_fx.strategies.protocol import ResearchStrategy


@dataclass(frozen=True, slots=True)
class ExperimentOutcome:
    """Measured evidence and eligibility for one strategy."""

    experiment_id: str
    strategy_id: str
    mode: ExperimentMode
    duration_seconds: float
    stage_seconds: dict[str, float]
    diagnostics: StrategyDiagnostics
    full_sample: BacktestResult
    holdout: BacktestResult
    holdout_validation: ValidationReport
    walk_forward_folds: tuple[WalkForwardFold, ...]
    stability: StabilitySummary | None
    sensitivity: tuple[SensitivityRun, ...]
    all_cost_scenarios_nonnegative: bool | None
    eligible: bool
    rejection_reasons: tuple[str, ...]

    @property
    def result(self) -> BacktestResult:
        return self.full_sample

    @property
    def holdout_passed(self) -> bool:
        return self.holdout_validation.passed


@dataclass(frozen=True, slots=True)
class StrategyExperimentRequest:
    """Complete immutable input for one strategy experiment."""

    manifest: StrategyManifest
    strategy: ResearchStrategy
    symbol: str
    bars: list[Bar]
    timeframe: Timeframe
    point: float
    contract_size: float
    backtest: BacktestSettings
    research: ResearchSettings
    experiments: ExperimentSettings
    mode: ExperimentMode = ExperimentMode.QUICK


def experiment_id(manifest: StrategyManifest, symbol: str, timeframe: Timeframe) -> str:
    payload = f"{manifest.id}|{manifest.kind}|{manifest.config}|{symbol}|{timeframe.value}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]
    return f"{manifest.id}-{symbol.lower()}-{timeframe.value.lower()}-{digest}"


def evaluate_eligibility(
    stability: StabilitySummary | None,
    settings: ExperimentSettings,
    *,
    holdout_passed: bool,
    all_cost_scenarios_nonnegative: bool | None,
    activity_passed: bool = True,
    complete_evidence: bool = True,
) -> tuple[bool, tuple[str, ...]]:
    """Apply research gates and fail closed on incomplete evidence."""
    reasons: list[str] = []
    eligibility = settings.eligibility
    if not activity_passed:
        reasons.append("insufficient_signal_frequency")
    if eligibility.require_holdout_pass and not holdout_passed:
        reasons.append("holdout_failed")
    if not complete_evidence:
        reasons.append("incomplete_research_mode")
    elif eligibility.require_walk_forward_stability and (stability is None or not stability.stable):
        reasons.append("walk_forward_unstable")
    if (
        complete_evidence
        and eligibility.require_all_cost_scenarios_nonnegative
        and not all_cost_scenarios_nonnegative
    ):
        reasons.append("cost_sensitivity_failed")
    if not eligibility.execution_enabled:
        reasons.append("execution_globally_disabled")
    return not reasons, tuple(reasons)


def _backtest_request(request: StrategyExperimentRequest, bars: list[Bar]) -> BacktestInput:
    return BacktestInput(
        symbol=request.symbol,
        bars=bars,
        timeframe=request.timeframe,
        point=request.point,
        contract_size=request.contract_size,
        strategy=request.strategy,
    )


def _cost_scenarios_pass(runs: tuple[SensitivityRun, ...]) -> bool:
    return bool(runs) and all(
        item.result.metrics.net_profit >= 0
        and item.result.metrics.expectancy >= 0
        and (item.result.metrics.profit_factor or 0.0) >= 1.0
        for item in runs
    )


def run_strategy_experiment(request: StrategyExperimentRequest) -> ExperimentOutcome:
    """Run the research evidence requested by the selected mode."""
    started = perf_counter()
    stages: dict[str, float] = {}
    stage_started = perf_counter()
    full_request = _backtest_request(request, request.bars)
    full_sample = run_backtest(full_request, request.backtest)
    stages["full_sample"] = perf_counter() - stage_started
    stage_started = perf_counter()
    _training, holdout_bars = holdout_split(
        request.bars, request.research.validation.in_sample_fraction
    )
    holdout = run_backtest(_backtest_request(request, holdout_bars), request.backtest)
    holdout_validation = validate_result(holdout, request.research.validation)
    stages["holdout"] = perf_counter() - stage_started
    stage_started = perf_counter()
    diagnostics = collect_diagnostics(request.strategy, request.symbol, request.bars, request.point)
    stages["diagnostics"] = perf_counter() - stage_started
    stage_started = perf_counter()
    folds: tuple[WalkForwardFold, ...] = ()
    stability: StabilitySummary | None = None
    sensitivity: tuple[SensitivityRun, ...] = ()
    cost_passed: bool | None = None
    complete = request.mode is ExperimentMode.FULL
    if complete:
        folds, stability = walk_forward(full_request, request.backtest, request.research)
        sensitivity = sensitivity_runs(full_request, request.backtest, request.research)
        cost_passed = _cost_scenarios_pass(sensitivity)
    activity_passed = (
        diagnostics.signal_frequency_percent
        >= request.experiments.experiments.minimum_signal_frequency_percent
        and full_sample.metrics.trade_count >= request.experiments.experiments.minimum_trades
    )
    eligible, reasons = evaluate_eligibility(
        stability,
        request.experiments,
        holdout_passed=holdout_validation.passed,
        all_cost_scenarios_nonnegative=cost_passed,
        activity_passed=activity_passed,
        complete_evidence=complete,
    )
    return ExperimentOutcome(
        experiment_id(request.manifest, request.symbol, request.timeframe),
        request.manifest.id,
        request.mode,
        perf_counter() - started,
        stages,
        diagnostics,
        full_sample,
        holdout,
        holdout_validation,
        folds,
        stability,
        sensitivity,
        cost_passed,
        eligible,
        reasons,
    )


def _result_payload(result: BacktestResult) -> dict[str, object]:
    return {"symbol": result.symbol, "metrics": asdict(result.metrics)}


def _outcome_payload(outcome: ExperimentOutcome) -> dict[str, object]:
    return {
        "experiment_id": outcome.experiment_id,
        "strategy_id": outcome.strategy_id,
        "mode": outcome.mode.value,
        "duration_seconds": outcome.duration_seconds,
        "stage_seconds": outcome.stage_seconds,
        "diagnostics": asdict(outcome.diagnostics),
        "full_sample": _result_payload(outcome.full_sample),
        "holdout": _result_payload(outcome.holdout),
        "holdout_validation": asdict(outcome.holdout_validation),
        "walk_forward": [
            {
                "number": fold.number,
                "train_start": fold.train_start,
                "train_end": fold.train_end,
                "test_start": fold.test_start,
                "test_end": fold.test_end,
                "metrics": asdict(fold.result.metrics),
            }
            for fold in outcome.walk_forward_folds
        ],
        "stability": asdict(outcome.stability) if outcome.stability else None,
        "sensitivity": [
            {"label": item.label, "metrics": asdict(item.result.metrics)}
            for item in outcome.sensitivity
        ],
        "all_cost_scenarios_nonnegative": outcome.all_cost_scenarios_nonnegative,
        "holdout_passed": outcome.holdout_passed,
        "eligible": outcome.eligible,
        "rejection_reasons": list(outcome.rejection_reasons),
    }


def export_outcomes(outcomes: tuple[ExperimentOutcome, ...], directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = directory / f"strategy_comparison_{timestamp}.json"
    destination.write_text(
        json.dumps([_outcome_payload(item) for item in outcomes], indent=2),
        encoding="utf-8",
    )
    return destination

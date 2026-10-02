"""Grandmaster FX command-line interface."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Annotated

import typer
from rich.panel import Panel

from grandmaster_fx import __version__
from grandmaster_fx.application.doctor import run_health_checks
from grandmaster_fx.backtest_console import render_backtest
from grandmaster_fx.backtesting import run_backtest
from grandmaster_fx.backtesting.engine import BacktestInput
from grandmaster_fx.config import Mt5Secrets, load_settings
from grandmaster_fx.config.backtest import load_backtest_settings
from grandmaster_fx.config.execution_profile import (
    ExecutionProfile,
    load_execution_runtime,
)
from grandmaster_fx.config.experiments import load_experiment_settings
from grandmaster_fx.config.loader import DEFAULT_CONFIG_PATH
from grandmaster_fx.config.research import load_research_settings
from grandmaster_fx.config.risk import load_risk_settings
from grandmaster_fx.config.strategy import load_strategy_settings
from grandmaster_fx.config.symbols import load_symbol_settings
from grandmaster_fx.console import console, render_checks
from grandmaster_fx.domain.market_data import Timeframe
from grandmaster_fx.domain.symbols import choose_symbol
from grandmaster_fx.exceptions import GrandmasterFxError, Mt5DataError
from grandmaster_fx.experiments.cache import load_bars, save_bars
from grandmaster_fx.experiments.modes import ExperimentMode
from grandmaster_fx.experiments.runner import (
    StrategyExperimentRequest,
    export_outcomes,
    run_strategy_experiment,
)
from grandmaster_fx.indicator_console import render_indicator_snapshot
from grandmaster_fx.indicators.snapshot import latest_snapshot
from grandmaster_fx.infrastructure.logging import configure_logging
from grandmaster_fx.infrastructure.mt5_gateway import Mt5Gateway
from grandmaster_fx.market_data.service import MarketDataService, default_export, export_bars
from grandmaster_fx.mt5_console import render_account, render_report, render_terminal
from grandmaster_fx.paper.worker import PaperWorker
from grandmaster_fx.pending.analysis import PendingAnalysisRequest
from grandmaster_fx.prediction_backtest_console import render_prediction_backtest
from grandmaster_fx.predictions.backtest import (
    PredictionBacktestStrategy,
    required_higher_bar_count,
)
from grandmaster_fx.predictions.config import load_prediction_settings
from grandmaster_fx.predictions.engine import PredictionEngine
from grandmaster_fx.predictions.filters import DirectionalStrategy, TradeDirection
from grandmaster_fx.research.analysis import analyze_result
from grandmaster_fx.research.exports import export_research
from grandmaster_fx.research.robustness import ablations, sensitivity_runs, walk_forward
from grandmaster_fx.research.robustness_exports import export_robustness
from grandmaster_fx.research.splits import holdout_split
from grandmaster_fx.research.validation import validate_result
from grandmaster_fx.research_console import render_research
from grandmaster_fx.robustness_console import render_robustness
from grandmaster_fx.strategies import evaluate_baseline
from grandmaster_fx.strategies.adapters import load_baseline_adapter
from grandmaster_fx.strategies.candidate_pack import (
    load_channel_mean_reversion,
    load_fibonacci_pullback,
    load_momentum_continuation,
    load_session_range_breakout,
)
from grandmaster_fx.strategies.donchian import load_donchian_strategy
from grandmaster_fx.strategies.extreme_reversion import load_extreme_mean_reversion
from grandmaster_fx.strategies.registry import StrategyRegistry
from grandmaster_fx.strategies.volatility_expansion import load_volatility_expansion
from grandmaster_fx.strategies.volatility_expansion_window import (
    load_volatility_expansion_window,
)
from grandmaster_fx.strategy_console import render_strategy_decision
from grandmaster_fx.symbol_console import render_symbol, render_symbols

if TYPE_CHECKING:
    from grandmaster_fx.execution.worker import ExecutionWorker
    from grandmaster_fx.strategies.protocol import ResearchStrategy

app = typer.Typer(
    name="grandmaster-fx",
    help="Safe, deterministic forex trading-system foundation.",
    no_args_is_help=True,
    add_completion=False,
    rich_markup_mode="rich",
)
mt5_app = typer.Typer(help="Read-only MetaTrader 5 connection diagnostics.", no_args_is_help=True)
app.add_typer(mt5_app, name="mt5")
symbols_app = typer.Typer(help="Discover and inspect currency symbols.", no_args_is_help=True)
app.add_typer(symbols_app, name="symbols")
data_app = typer.Typer(help="Retrieve and export validated UTC market data.", no_args_is_help=True)
app.add_typer(data_app, name="data")
indicators_app = typer.Typer(
    help="Calculate deterministic numerical indicators.", no_args_is_help=True
)
app.add_typer(indicators_app, name="indicators")
strategy_app = typer.Typer(
    help="Evaluate explainable deterministic strategy decisions.", no_args_is_help=True
)
app.add_typer(strategy_app, name="strategy")
backtest_app = typer.Typer(help="Run deterministic historical simulations.", no_args_is_help=True)
app.add_typer(backtest_app, name="backtest")
research_app = typer.Typer(
    help="Analyze robustness and out-of-sample performance.", no_args_is_help=True
)
app.add_typer(research_app, name="research")
experiments_app = typer.Typer(
    help="Run reproducible multi-strategy experiments.", no_args_is_help=True
)
app.add_typer(experiments_app, name="experiments")
predictions_app = typer.Typer(
    help="Inspect regime-aware, multi-timeframe strategy predictions.",
    no_args_is_help=True,
)
app.add_typer(predictions_app, name="predictions")
paper_app = typer.Typer(help="Continuous broker-free paper execution.", no_args_is_help=True)
app.add_typer(paper_app, name="paper")
pending_app = typer.Typer(help="One-shot pending-order analysis.", no_args_is_help=True)
app.add_typer(pending_app, name="pending")
demo_app = typer.Typer(help="Continuous live-demo execution manager.", no_args_is_help=True)
app.add_typer(demo_app, name="demo")
live_app = typer.Typer(help="Continuous real-money execution manager.", no_args_is_help=True)
app.add_typer(live_app, name="live")

EXPERIMENT_STRATEGY_OPTION = typer.Option(None, "--strategy")
EXPERIMENT_MODE_OPTION = typer.Option(ExperimentMode.QUICK, "--mode")
DEFAULT_EXPERIMENT_CACHE = True
EXPERIMENT_CACHE_OPTION = typer.Option(DEFAULT_EXPERIMENT_CACHE, "--cache/--no-cache")


def _load_strategy_registry() -> StrategyRegistry:
    registry = StrategyRegistry()
    registry.register("baseline", lambda item: load_baseline_adapter(item.config))
    registry.register(
        "donchian_breakout",
        lambda item: load_donchian_strategy(item.config),
    )
    registry.register(
        "volatility_expansion",
        lambda item: load_volatility_expansion(item.config),
    )
    registry.register(
        "volatility_expansion_window",
        lambda item: load_volatility_expansion_window(item.config),
    )
    registry.register(
        "extreme_mean_reversion",
        lambda item: load_extreme_mean_reversion(item.config),
    )
    registry.register(
        "session_range_breakout",
        lambda item: load_session_range_breakout(item.config),
    )
    registry.register(
        "fibonacci_pullback",
        lambda item: load_fibonacci_pullback(item.config),
    )
    registry.register(
        "channel_mean_reversion",
        lambda item: load_channel_mean_reversion(item.config),
    )
    registry.register(
        "momentum_continuation",
        lambda item: load_momentum_continuation(item.config),
    )
    return registry


def _require_selected_strategies(selected: tuple[object, ...], strategy: str | None) -> None:
    """Reject an empty experiment selection outside the command try block."""
    if not selected:
        message = f"No enabled strategy matched: {strategy}"
        raise ValueError(message)


ConfigOption = Annotated[
    Path,
    typer.Option(
        "--config",
        "-c",
        help="Path to application TOML.",
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
    ),
]


def _version_callback(value: bool) -> None:
    if value:
        console.print(f"grandmaster-fx {__version__}")
        raise typer.Exit


@app.callback()
def root(
    version: Annotated[
        bool | None,
        typer.Option("--version", callback=_version_callback, is_eager=True, help="Show version."),
    ] = None,
) -> None:
    """Grandmaster FX project commands."""


@app.command()
def doctor(config: ConfigOption = DEFAULT_CONFIG_PATH) -> None:
    """Validate local configuration and foundational safety controls."""
    try:
        settings = load_settings(config)
        logger = configure_logging(settings.app.log_level, settings.app.log_directory)
        logger.info("Starting local health checks")
        results = run_health_checks(settings, config)
        render_checks(results)
        if not all(result.ok for result in results):
            raise typer.Exit(code=1)
        console.print(Panel.fit("Foundation is healthy.", style="green"))
    except GrandmasterFxError as error:
        _exit_with_error(error)


@app.command("show-config")
def show_config(config: ConfigOption = DEFAULT_CONFIG_PATH) -> None:
    """Display non-secret application configuration."""
    try:
        settings = load_settings(config)
        console.print_json(data=settings.model_dump(mode="json"))
    except GrandmasterFxError as error:
        _exit_with_error(error)


def _with_gateway(action: str) -> None:
    try:
        secrets = Mt5Secrets()
        settings = load_settings()
        with Mt5Gateway(secrets) as gateway:
            if action == "doctor":
                from grandmaster_fx.application.mt5_diagnostics import inspect_connection

                render_report(inspect_connection(gateway))
            elif action == "terminal":
                render_terminal(gateway.terminal())
                gateway.account().verify_execution_safety(settings.execution.allow_live_account)
            else:
                render_account(gateway.account())
    except GrandmasterFxError as error:
        _exit_with_error(error)


@mt5_app.command("doctor")
def mt5_doctor() -> None:
    """Initialize MT5 and validate the terminal and connection."""
    _with_gateway("doctor")


@mt5_app.command("terminal")
def mt5_terminal() -> None:
    """Display read-only terminal diagnostics."""
    _with_gateway("terminal")


@mt5_app.command("account")
def mt5_account() -> None:
    """Display a sanitized account summary."""
    _with_gateway("account")


@symbols_app.command("list")
def symbols_list() -> None:
    """List currency-only symbols exposed by the connected terminal."""
    try:
        settings = load_symbol_settings()
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            render_symbols(gateway.symbols(settings.symbols.allowed_currencies))
    except GrandmasterFxError as error:
        _exit_with_error(error)


@symbols_app.command("inspect")
def symbols_inspect(pair: str) -> None:
    """Resolve and inspect one normalized currency pair."""
    try:
        settings = load_symbol_settings()
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            candidates = gateway.symbols(settings.symbols.allowed_currencies)
            resolved = choose_symbol(candidates, pair)
            if not resolved.selected:
                gateway.select_symbol(resolved.name)
                resolved = gateway.symbol(resolved.name, settings.symbols.allowed_currencies)
            render_symbol(resolved)
    except GrandmasterFxError as error:
        _exit_with_error(error)


@symbols_app.command("validate")
def symbols_validate(pairs: list[str]) -> None:
    """Validate normalized pairs against broker metadata."""
    try:
        settings = load_symbol_settings()
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            candidates = gateway.symbols(settings.symbols.allowed_currencies)
            resolved = [choose_symbol(candidates, pair) for pair in pairs]
            invalid = [
                item.name
                for item in resolved
                if not item.trade_enabled or item.tick_size <= 0 or item.volume_step <= 0
            ]
            render_symbols(resolved)
            if invalid:
                raise Mt5DataError(f"Ineligible symbols: {', '.join(invalid)}")
    except GrandmasterFxError as error:
        _exit_with_error(error)


@data_app.command("tick")
def data_tick(pair: str) -> None:
    """Display the latest validated bid/ask tick."""
    try:
        settings = load_symbol_settings()
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            name, tick = MarketDataService(
                gateway, settings.symbols.allowed_currencies
            ).latest_tick(pair)
            console.print(
                f"[bold]{pair.upper()} | {name}[/bold]  {tick.time.isoformat()}  bid={tick.bid:g}  ask={tick.ask:g}  spread={tick.spread:g}"
            )
    except GrandmasterFxError as error:
        _exit_with_error(error)


@data_app.command("bars")
def data_bars(pair: str, timeframe: Timeframe = Timeframe.M1, count: int = 100) -> None:
    """Display a summary of completed UTC candles."""
    try:
        settings = load_symbol_settings()
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            name, bars = MarketDataService(gateway, settings.symbols.allowed_currencies).bars(
                pair, timeframe, count
            )
            first, last = bars[0], bars[-1]
            console.print(
                f"[bold]{pair.upper()} | {name} | {timeframe.value}[/bold]  bars={len(bars)}  {first.time.isoformat()} -> {last.time.isoformat()}  last_close={last.close:g}"
            )
    except GrandmasterFxError as error:
        _exit_with_error(error)


@data_app.command("export")
def data_export(
    pair: str, timeframe: Timeframe = Timeframe.M1, count: int = 1000, output_format: str = "csv"
) -> None:
    """Export completed UTC candles to CSV."""
    try:
        if output_format != "csv":
            raise Mt5DataError("Format must be csv")
        settings = load_symbol_settings()
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            _, bars = MarketDataService(gateway, settings.symbols.allowed_currencies).bars(
                pair, timeframe, count
            )
            path = export_bars(bars, default_export(pair, timeframe, output_format))
            console.print(f"Exported {len(bars)} bars to [bold]{path.resolve()}[/bold]")
    except GrandmasterFxError as error:
        _exit_with_error(error)


@indicators_app.command("inspect")
def indicators_inspect(pair: str, timeframe: Timeframe = Timeframe.M1, count: int = 200) -> None:
    """Calculate the latest baseline indicators from completed candles."""
    try:
        settings = load_symbol_settings()
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            name, bars = MarketDataService(gateway, settings.symbols.allowed_currencies).bars(
                pair, timeframe, count
            )
            render_indicator_snapshot(pair, name, timeframe.value, latest_snapshot(bars))
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@strategy_app.command("inspect")
def strategy_inspect(pair: str, timeframe: Timeframe = Timeframe.M1, count: int = 200) -> None:
    """Evaluate the baseline scalper on completed candles without trading."""
    try:
        symbol_settings = load_symbol_settings()
        strategy_settings = load_strategy_settings()
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            service = MarketDataService(gateway, symbol_settings.symbols.allowed_currencies)
            name, bars = service.bars(pair, timeframe, count)
            metadata = gateway.symbol(name, symbol_settings.symbols.allowed_currencies)
            decision = evaluate_baseline(name, bars, metadata.point, strategy_settings)
            render_strategy_decision(decision, timeframe.value)
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@backtest_app.command("run")
def backtest_run(
    pair: str,
    timeframe: Timeframe = Timeframe.M5,
    count: int = 10000,
    strategy: str = "baseline_scalper",
    predictions: bool = typer.Option(
        True,  # noqa: FBT003
        "--predictions/--no-predictions",
    ),
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Run a strategy backtest with optional no-lookahead prediction gates."""
    from grandmaster_fx.predictions.backtest import (
        PredictionBacktestStrategy,
        required_higher_bar_count,
    )

    try:
        symbols = load_symbol_settings()
        configuration = load_backtest_settings()
        experiments = load_experiment_settings()
        manifest = next(
            (item for item in experiments.strategies if item.id == strategy and item.enabled),
            None,
        )
        if manifest is None:
            message = f"Strategy '{strategy}' not found or disabled"
            raise ValueError(message)  # noqa: TRY301
        implementation = DirectionalStrategy(_load_strategy_registry().create(manifest), direction)
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            service = MarketDataService(gateway, symbols.symbols.allowed_currencies)
            name, bars = service.bars(pair, timeframe, count)
            metadata = gateway.symbol(name, symbols.symbols.allowed_currencies)
            filtered = None
            selected: ResearchStrategy = implementation
            if predictions:
                prediction_settings = load_prediction_settings()
                higher = prediction_settings.confirmation.higher_timeframe
                higher_count = required_higher_bar_count(count, timeframe, higher)
                _higher_name, higher_bars = service.bars(pair, higher, higher_count)
                filtered = PredictionBacktestStrategy(
                    strategy,
                    implementation,
                    PredictionEngine(prediction_settings),
                    higher_bars,
                )
                selected = filtered
            request = BacktestInput(
                symbol=name,
                bars=bars,
                timeframe=timeframe,
                point=metadata.point,
                contract_size=metadata.contract_size,
                strategy=selected,
            )
            render_backtest(run_backtest(request, configuration))
            if filtered is not None:
                render_prediction_backtest(filtered.report())
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@research_app.command("validate")
def research_validate(
    pair: str,
    timeframe: Timeframe = Timeframe.M5,
    count: int = 20000,
    strategy: str = "baseline_scalper",
    predictions: bool = typer.Option(
        True,  # noqa: FBT003
        "--predictions/--no-predictions",
    ),
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Validate one selected strategy on a chronological holdout."""
    try:
        symbols = load_symbol_settings()
        backtest = load_backtest_settings()
        research = load_research_settings()
        experiments = load_experiment_settings()
        manifest = next(
            (item for item in experiments.strategies if item.id == strategy and item.enabled),
            None,
        )
        if manifest is None:
            message = f"Strategy '{strategy}' not found or disabled"
            raise ValueError(message)  # noqa: TRY301
        implementation = DirectionalStrategy(_load_strategy_registry().create(manifest), direction)
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            service = MarketDataService(gateway, symbols.symbols.allowed_currencies)
            name, bars = service.bars(pair, timeframe, count)
            metadata = gateway.symbol(name, symbols.symbols.allowed_currencies)
            _train, test = holdout_split(
                bars,
                research.validation.in_sample_fraction,
            )
            filtered = None
            selected: ResearchStrategy = implementation
            if predictions:
                prediction_settings = load_prediction_settings()
                higher = prediction_settings.confirmation.higher_timeframe
                higher_count = required_higher_bar_count(count, timeframe, higher)
                _higher_name, higher_bars = service.bars(pair, higher, higher_count)
                filtered = PredictionBacktestStrategy(
                    strategy,
                    implementation,
                    PredictionEngine(prediction_settings),
                    higher_bars,
                )
                selected = filtered
            request = BacktestInput(
                symbol=name,
                bars=test,
                timeframe=timeframe,
                point=metadata.point,
                contract_size=metadata.contract_size,
                strategy=selected,
            )
            result = run_backtest(request, backtest)
            analysis = analyze_result(result)
            validation = validate_result(result, research.validation)
            export_research(analysis, validation, research.exports.directory)
            render_research(analysis, validation)
            if filtered is not None:
                render_prediction_backtest(filtered.report())
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@research_app.command("robustness")
def research_robustness(
    pair: str,
    timeframe: Timeframe = Timeframe.M5,
    count: int = 20000,
    strategy: str = "baseline_scalper",
    predictions: bool = typer.Option(
        True,  # noqa: FBT003
        "--predictions/--no-predictions",
    ),
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Run walk-forward and cost sensitivity for one selected strategy."""
    try:
        symbols = load_symbol_settings()
        backtest = load_backtest_settings()
        research = load_research_settings()
        experiments = load_experiment_settings()
        manifest = next(
            (item for item in experiments.strategies if item.id == strategy and item.enabled),
            None,
        )
        if manifest is None:
            message = f"Strategy '{strategy}' not found or disabled"
            raise ValueError(message)  # noqa: TRY301
        implementation = DirectionalStrategy(_load_strategy_registry().create(manifest), direction)
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            service = MarketDataService(gateway, symbols.symbols.allowed_currencies)
            name, bars = service.bars(pair, timeframe, count)
            metadata = gateway.symbol(name, symbols.symbols.allowed_currencies)
            filtered = None
            selected: ResearchStrategy = implementation
            if predictions:
                prediction_settings = load_prediction_settings()
                higher = prediction_settings.confirmation.higher_timeframe
                higher_count = required_higher_bar_count(count, timeframe, higher)
                _higher_name, higher_bars = service.bars(pair, higher, higher_count)
                filtered = PredictionBacktestStrategy(
                    strategy,
                    implementation,
                    PredictionEngine(prediction_settings),
                    higher_bars,
                )
                selected = filtered
            request = BacktestInput(
                symbol=name,
                bars=bars,
                timeframe=timeframe,
                point=metadata.point,
                contract_size=metadata.contract_size,
                strategy=selected,
            )
            folds, stability = walk_forward(request, backtest, research)
            sensitivity = sensitivity_runs(request, backtest, research)
            baseline = run_backtest(request, backtest)
            diagnostic = ablations(baseline)
            export_robustness(
                name,
                research.exports.directory,
                folds,
                stability,
                sensitivity,
                diagnostic,
            )
            render_robustness(name, folds, stability, sensitivity, diagnostic)
            if filtered is not None:
                render_prediction_backtest(filtered.report())
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@experiments_app.command("compare")
def experiments_compare(
    pair: str,
    timeframe: Timeframe = Timeframe.M5,
    count: int = 10000,
    strategy: str | None = EXPERIMENT_STRATEGY_OPTION,
    mode: ExperimentMode = EXPERIMENT_MODE_OPTION,
    use_cache: bool = EXPERIMENT_CACHE_OPTION,
) -> None:
    """Compare selected strategies with progress, caching, and research modes."""
    try:
        symbols = load_symbol_settings()
        backtest = load_backtest_settings()
        research = load_research_settings()
        experiments = load_experiment_settings()
        registry = _load_strategy_registry()
        selected = tuple(
            item
            for item in experiments.strategies
            if item.enabled and (strategy is None or item.id == strategy)
        )
        _require_selected_strategies(selected, strategy)
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            service = MarketDataService(gateway, symbols.symbols.allowed_currencies)
            resolved = service.resolve(pair)
            bars = load_bars(resolved, timeframe, count) if use_cache else None
            if bars is None:
                name, bars = service.bars(pair, timeframe, count)
                if use_cache:
                    save_bars(name, timeframe, count, bars)
            else:
                name = resolved
                console.print(f"Loaded {len(bars)} candles from local cache.")
            metadata = gateway.symbol(name, symbols.symbols.allowed_currencies)
            outcomes_list = []
            for position, manifest in enumerate(selected, 1):
                console.print(
                    f"[{position}/{len(selected)}] Running {manifest.id} in {mode.value} mode..."
                )
                outcome = run_strategy_experiment(
                    StrategyExperimentRequest(
                        manifest=manifest,
                        strategy=registry.create(manifest),
                        symbol=name,
                        bars=bars,
                        timeframe=timeframe,
                        point=metadata.point,
                        contract_size=metadata.contract_size,
                        backtest=backtest,
                        research=research,
                        experiments=experiments,
                        mode=mode,
                    )
                )
                outcomes_list.append(outcome)
                console.print(
                    f"Completed {manifest.id} in {outcome.duration_seconds:.2f}s: "
                    f"trades={outcome.full_sample.metrics.trade_count} "
                    f"signals={outcome.diagnostics.actionable_signals} "
                    f"frequency={outcome.diagnostics.signal_frequency_percent:.3f}%"
                )
            outcomes = tuple(outcomes_list)
            destination = export_outcomes(outcomes, research.exports.directory)
            console.print(f"Exported strategy comparison to [bold]{destination}[/bold]")
            for outcome in outcomes:
                folds = (
                    f"{outcome.stability.profitable_folds}/{outcome.stability.folds}"
                    if outcome.stability
                    else "not-run"
                )
                console.print(
                    f"{outcome.strategy_id}: mode={outcome.mode.value} "
                    f"full_return={outcome.full_sample.metrics.total_return_percent:.2f}% "
                    f"holdout_return={outcome.holdout.metrics.total_return_percent:.2f}% "
                    f"holdout_pf={outcome.holdout.metrics.profit_factor or 0.0:.3f} "
                    f"profitable_folds={folds} "
                    f"cost_passed={outcome.all_cost_scenarios_nonnegative} "
                    f"eligible={outcome.eligible} "
                    f"reasons={','.join(outcome.rejection_reasons)}"
                )
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


def _paper_worker(
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> tuple[Mt5Gateway, PaperWorker]:
    from grandmaster_fx.paper.config import load_paper_worker_settings

    settings = load_symbol_settings()
    gateway = Mt5Gateway(Mt5Secrets())
    gateway.connect()
    gateway.account()
    candidates = gateway.symbols(settings.symbols.allowed_currencies)
    selected_pairs = (symbol,) if symbol is not None else settings.symbols.preferred
    resolved = tuple(
        (chosen.name, chosen.point)
        for pair in selected_pairs
        for chosen in (choose_symbol(candidates, pair),)
    )
    return gateway, PaperWorker(
        gateway, resolved, load_paper_worker_settings(), direction=direction
    )


def _pending_inputs(
    pair: str,
    strategy_id: str,
    timeframe: Timeframe,
    count: int,
    direction: TradeDirection,
    predictions: bool,
) -> tuple[Mt5Gateway, PendingAnalysisRequest]:

    symbols = load_symbol_settings()
    experiments = load_experiment_settings()
    manifest = next(
        (item for item in experiments.strategies if item.id == strategy_id and item.enabled),
        None,
    )
    if manifest is None:
        message = f"Strategy '{strategy_id}' not found or disabled"
        raise ValueError(message)
    gateway = Mt5Gateway(Mt5Secrets())
    gateway.connect()
    gateway.account()
    service = MarketDataService(gateway, symbols.symbols.allowed_currencies)
    name, bars = service.bars(pair, timeframe, count)
    metadata = gateway.symbol(name, symbols.symbols.allowed_currencies)
    implementation = _load_strategy_registry().create(manifest)
    engine = PredictionEngine(load_prediction_settings()) if predictions else None
    higher_bars = None
    if engine is not None:
        higher = engine.settings.confirmation.higher_timeframe
        higher_count = required_higher_bar_count(count, timeframe, higher)
        _higher_name, higher_bars = service.bars(pair, higher, higher_count)
    request = PendingAnalysisRequest(
        strategy_id=strategy_id,
        strategy=implementation,
        symbol=name,
        timeframe=timeframe,
        bars=bars,
        point=metadata.point,
        direction=direction.value,
        prediction_engine=engine,
        higher_bars=higher_bars,
    )
    return gateway, request


@pending_app.command("inspect")
def pending_inspect(
    pair: str,
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    count: int = 200,
    direction: TradeDirection = TradeDirection.ALL,
    predictions: bool = typer.Option(True, "--predictions/--no-predictions"),  # noqa: FBT003
) -> None:
    """Analyze once with optional prediction gates and print a pending plan."""
    from grandmaster_fx.config.pending_orders import load_pending_order_settings
    from grandmaster_fx.pending.runtime import inspect_pending

    gateway, request = _pending_inputs(pair, strategy, timeframe, count, direction, predictions)
    try:
        console.print_json(data=inspect_pending(request, load_pending_order_settings()))
    finally:
        gateway.close()


@paper_app.command("pending-place")
def paper_pending_place(
    pair: str,
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    count: int = 200,
    direction: TradeDirection = TradeDirection.ALL,
    predictions: bool = typer.Option(True, "--predictions/--no-predictions"),  # noqa: FBT003
) -> None:
    """Analyze once with optional prediction gates, persist a paper plan, and exit."""
    from grandmaster_fx.config.pending_orders import load_pending_order_settings
    from grandmaster_fx.pending.runtime import PendingPlacementRequest, place_paper_pending

    gateway, analysis = _pending_inputs(pair, strategy, timeframe, count, direction, predictions)
    try:
        console.print_json(
            data=place_paper_pending(
                PendingPlacementRequest(
                    analysis=analysis,
                    settings=load_pending_order_settings(),
                )
            )
        )
    finally:
        gateway.close()


@paper_app.command("pending-list")
def paper_pending_list() -> None:
    """List restart-safe paper pending orders."""
    from grandmaster_fx.pending.runtime import DEFAULT_PAPER_PENDING_PATH, record_payload
    from grandmaster_fx.pending.service import PendingOrderService
    from grandmaster_fx.pending.store import PendingOrderStore

    service = PendingOrderService(PendingOrderStore(DEFAULT_PAPER_PENDING_PATH))
    console.print_json(data={"orders": [record_payload(item) for item in service.list()]})


@paper_app.command("pending-reconcile")
def paper_pending_reconcile() -> None:
    """Reconcile active paper pending orders against the latest completed candles once."""
    from grandmaster_fx.pending.runtime import (
        DEFAULT_PAPER_PENDING_PATH,
        reconcile_paper_pending,
    )
    from grandmaster_fx.pending.service import PendingOrderService
    from grandmaster_fx.pending.store import PendingOrderStore

    symbol_settings = load_symbol_settings()
    gateway = Mt5Gateway(Mt5Secrets())
    gateway.connect()
    try:
        gateway.account()
        service = PendingOrderService(PendingOrderStore(DEFAULT_PAPER_PENDING_PATH))
        market = MarketDataService(gateway, symbol_settings.symbols.allowed_currencies)
        completed = {}
        for record in service.active():
            _name, bars = market.bars(record.plan.symbol, record.plan.timeframe, 1)
            completed[record.plan.symbol] = bars[-1]
        console.print_json(data=reconcile_paper_pending(completed))
    finally:
        gateway.close()


@pending_app.command("backtest")
def pending_backtest(
    pair: str,
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    count: int = 20000,
    direction: TradeDirection = TradeDirection.ALL,
    predictions: bool = typer.Option(
        True,  # noqa: FBT003
        "--predictions/--no-predictions",
    ),
) -> None:
    """Run a full pending-entry historical backtest."""
    from dataclasses import asdict

    from grandmaster_fx.config.pending_orders import load_pending_order_settings
    from grandmaster_fx.pending.historical import run_pending_backtest

    gateway, analysis = _pending_inputs(pair, strategy, timeframe, count, direction, predictions)
    try:
        metadata = gateway.symbol(
            analysis.symbol, load_symbol_settings().symbols.allowed_currencies
        )
        selected: ResearchStrategy = analysis.strategy
        if analysis.prediction_engine is not None and analysis.higher_bars is not None:
            selected = PredictionBacktestStrategy(
                analysis.strategy_id,
                analysis.strategy,
                analysis.prediction_engine,
                analysis.higher_bars,
            )
        request = BacktestInput(
            analysis.symbol,
            analysis.bars,
            timeframe,
            analysis.point,
            metadata.contract_size,
            DirectionalStrategy(selected, direction),
        )
        outcome = run_pending_backtest(
            request, load_backtest_settings(), load_pending_order_settings()
        )
        render_backtest(outcome.result)
        report = asdict(outcome.diagnostics) | {
            "trigger_rate_percent": outcome.diagnostics.trigger_rate_percent,
            "expiration_rate_percent": outcome.diagnostics.expiration_rate_percent,
        }
        console.print_json(data=report)
    finally:
        gateway.close()


@demo_app.command("pending-place")
def demo_pending_place(
    pair: str,
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    count: int = 200,
    direction: TradeDirection = TradeDirection.ALL,
    predictions: bool = typer.Option(
        True,  # noqa: FBT003
        "--predictions/--no-predictions",
    ),
) -> None:
    """Analyze once and place one MT5 demo pending order."""
    from grandmaster_fx.config.pending_orders import load_pending_order_settings
    from grandmaster_fx.execution.risk import RiskManager
    from grandmaster_fx.pending.analysis import analyze_pending
    from grandmaster_fx.pending.demo import DemoPendingPlacement, place_demo_pending
    from grandmaster_fx.pending.planner import plan_pending_order

    gateway, request = _pending_inputs(pair, strategy, timeframe, count, direction, predictions)
    try:
        account = gateway.account()
        account.require_demo()
        analysis = analyze_pending(request)
        if not analysis.accepted:
            console.print_json(data={"placed": False, "reason": analysis.reason})
            return
        plan = plan_pending_order(
            request.strategy_id,
            request.symbol,
            request.timeframe,
            analysis.filtered,
            request.bars,
            load_pending_order_settings(),
        )
        if plan is None:
            console.print_json(data={"placed": False, "reason": "no_actionable_pending_setup"})
            return
        runtime = load_execution_runtime(ExecutionProfile.DEMO, load_settings())
        symbol = gateway.symbol(request.symbol, load_symbol_settings().symbols.allowed_currencies)
        console.print_json(
            data=place_demo_pending(
                gateway,
                DemoPendingPlacement(
                    plan,
                    symbol,
                    account.balance,
                    runtime.settings,
                    RiskManager(load_risk_settings()),
                ),
            )
        )
    finally:
        gateway.close()


@demo_app.command("pending-list")
def demo_pending_list() -> None:
    from grandmaster_fx.pending.demo import list_demo_pending

    runtime = load_execution_runtime(ExecutionProfile.DEMO, load_settings())
    with Mt5Gateway(Mt5Secrets()) as gateway:
        console.print_json(data=list_demo_pending(gateway, runtime.settings.execution.magic))


@demo_app.command("pending-reconcile")
def demo_pending_reconcile() -> None:
    from grandmaster_fx.pending.demo import reconcile_demo_pending

    runtime = load_execution_runtime(ExecutionProfile.DEMO, load_settings())
    with Mt5Gateway(Mt5Secrets()) as gateway:
        console.print_json(data=reconcile_demo_pending(gateway, runtime.settings.execution.magic))


@demo_app.command("pending-cancel")
def demo_pending_cancel(ticket: int) -> None:
    runtime = load_execution_runtime(ExecutionProfile.DEMO, load_settings())
    with Mt5Gateway(Mt5Secrets()) as gateway:
        gateway.account().require_demo()
        console.print_json(
            data={
                "ticket": ticket,
                "canceled": gateway.cancel_pending_order(
                    ticket, runtime.settings.execution.magic, runtime.settings.execution.dry_run
                ),
            }
        )


@live_app.command("pending-place")
def live_pending_place(
    pair: str,
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    count: int = 200,
    direction: TradeDirection = TradeDirection.ALL,
    predictions: bool = typer.Option(
        True,  # noqa: FBT003
        "--predictions/--no-predictions",
    ),
) -> None:
    """Build and broker-validate one real-account pending request."""
    from grandmaster_fx.config.pending_orders import load_pending_order_settings
    from grandmaster_fx.execution.journal import ExecutionJournal
    from grandmaster_fx.execution.risk import RiskManager
    from grandmaster_fx.pending.analysis import analyze_pending
    from grandmaster_fx.pending.live import LivePendingPlacement, place_live_pending
    from grandmaster_fx.pending.planner import plan_pending_order

    gateway, request = _pending_inputs(pair, strategy, timeframe, count, direction, predictions)
    try:
        account = gateway.account()
        account.require_real()
        runtime = load_execution_runtime(ExecutionProfile.LIVE, load_settings())
        analysis = analyze_pending(request)
        if not analysis.accepted:
            console.print_json(data={"placed": False, "reason": analysis.reason})
            return
        plan = plan_pending_order(
            request.strategy_id,
            request.symbol,
            request.timeframe,
            analysis.filtered,
            request.bars,
            load_pending_order_settings(),
        )
        if plan is None:
            console.print_json(data={"placed": False, "reason": "no_actionable_pending_setup"})
            return
        symbol = gateway.symbol(
            request.symbol,
            load_symbol_settings().symbols.allowed_currencies,
        )
        console.print_json(
            data=place_live_pending(
                gateway,
                LivePendingPlacement(
                    plan=plan,
                    symbol=symbol,
                    balance=account.balance,
                    settings=runtime.settings,
                    risk=RiskManager(load_risk_settings()),
                    journal=ExecutionJournal(runtime.journal_path),
                    registry_path=runtime.journal_path.parent / "pending_orders.json",
                ),
            )
        )
    finally:
        gateway.close()


@live_app.command("pending-list")
def live_pending_list() -> None:
    """List live-profile pending orders on the connected REAL account."""
    from grandmaster_fx.pending.live import list_live_pending

    runtime = load_execution_runtime(ExecutionProfile.LIVE, load_settings())
    with Mt5Gateway(Mt5Secrets()) as gateway:
        console.print_json(data=list_live_pending(gateway, runtime.settings.execution.magic))


@live_app.command("pending-reconcile")
def live_pending_reconcile() -> None:
    """Reconcile live-profile pending orders and positions without changing them."""
    from grandmaster_fx.pending.live import reconcile_live_pending

    runtime = load_execution_runtime(ExecutionProfile.LIVE, load_settings())
    with Mt5Gateway(Mt5Secrets()) as gateway:
        console.print_json(
            data=reconcile_live_pending(
                gateway,
                runtime.settings.execution.magic,
                runtime.journal_path.parent / "pending_orders.json",
            )
        )


@live_app.command("pending-cancel")
def live_pending_cancel(ticket: int) -> None:
    """Cancel one live-profile pending order on the connected REAL account."""
    runtime = load_execution_runtime(ExecutionProfile.LIVE, load_settings())
    with Mt5Gateway(Mt5Secrets()) as gateway:
        gateway.account().require_real()
        console.print_json(
            data={
                "ticket": ticket,
                "canceled": gateway.cancel_pending_order(
                    ticket, runtime.settings.execution.magic, runtime.settings.execution.dry_run
                ),
            }
        )


@paper_app.command("status")
def paper_status(
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Display restart-safe paper account and position state."""
    gateway, worker = _paper_worker(symbol, direction)
    try:
        console.print_json(data=worker.status())
    finally:
        gateway.close()


@paper_app.command("cycle")
def paper_cycle(
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Run one paper monitoring and signal-scanning cycle."""
    gateway, worker = _paper_worker(symbol, direction)
    try:
        console.print_json(data=worker.cycle())
    finally:
        gateway.close()


@paper_app.command("run")
def paper_run(
    maximum_cycles: int | None = None,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Continuously monitor prices and manage simulated positions."""
    gateway, worker = _paper_worker(symbol, direction)
    try:
        worker.run(maximum_cycles)
    finally:
        gateway.close()


@paper_app.command("stop")
def paper_stop() -> None:
    """Request a running paper worker to stop after its current cycle."""
    stop_path = Path("data/paper/STOP")
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    console.print("Paper worker stop requested.")


def _create_worker(
    profile: ExecutionProfile,
    strategy_id: str,
    timeframe: Timeframe,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> tuple[Mt5Gateway, ExecutionWorker]:
    from grandmaster_fx.execution.journal import ExecutionJournal
    from grandmaster_fx.execution.manager import ExecutionManager
    from grandmaster_fx.execution.risk import RiskManager
    from grandmaster_fx.execution.worker import ExecutionWorker

    app_settings = load_settings()
    symbol_settings = load_symbol_settings()
    runtime = load_execution_runtime(profile, app_settings)
    risk_settings = load_risk_settings()
    experiments = load_experiment_settings()

    manifest = next((item for item in experiments.strategies if item.id == strategy_id), None)
    if manifest is None:
        message = f"Strategy '{strategy_id}' not found in experiments.toml"
        raise ValueError(message)

    registry = _load_strategy_registry()
    strategy = registry.create(manifest)

    gateway = Mt5Gateway(Mt5Secrets())
    gateway.connect()

    # The ExecutionManager decides whether to enforce demo via account checks
    risk_manager = RiskManager(risk_settings)
    manager = ExecutionManager(
        gateway=gateway,
        settings=runtime.settings,
        risk_manager=risk_manager,
        allowed_currencies=symbol_settings.symbols.allowed_currencies,
        allow_live_account=profile is ExecutionProfile.LIVE,
        journal=ExecutionJournal(runtime.journal_path),
    )

    worker = ExecutionWorker(
        gateway=gateway,
        manager=manager,
        strategy=strategy,
        timeframe=timeframe,
        symbols=(symbol,) if symbol is not None else symbol_settings.symbols.preferred,
        allowed_currencies=symbol_settings.symbols.allowed_currencies,
        prediction_engine=PredictionEngine(load_prediction_settings()),
        strategy_id=strategy_id,
        direction=direction,
        stop_path=runtime.stop_path,
        consumed_path=runtime.consumed_path,
        profile=profile.value,
    )
    return gateway, worker


@demo_app.command("status")
def demo_status(
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Display real demo account and position state."""
    try:
        gateway, worker = _create_worker(
            ExecutionProfile.DEMO, strategy, timeframe, symbol, direction
        )
        try:
            # We strictly enforce demo behavior for demo commands
            gateway.account().require_demo()
            console.print_json(data=worker.status())
        finally:
            gateway.close()
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@demo_app.command("cycle")
def demo_cycle(
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Run one demo execution and signal-scanning cycle."""
    try:
        gateway, worker = _create_worker(
            ExecutionProfile.DEMO, strategy, timeframe, symbol, direction
        )
        try:
            gateway.account().require_demo()
            console.print_json(data=worker.cycle())
        finally:
            gateway.close()
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@demo_app.command("run")
def demo_run(
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    maximum_cycles: int | None = None,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Continuously run the demo execution manager."""
    try:
        gateway, worker = _create_worker(
            ExecutionProfile.DEMO, strategy, timeframe, symbol, direction
        )
        try:
            gateway.account().require_demo()
            worker.run(maximum_cycles)
        finally:
            gateway.close()
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@demo_app.command("dashboard")
def demo_dashboard(
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    maximum_cycles: int | None = None,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Run a continuously refreshing demo execution dashboard."""
    try:
        gateway, worker = _create_worker(
            ExecutionProfile.DEMO, strategy, timeframe, symbol, direction
        )
        try:
            gateway.account().require_demo()
            worker.run_dashboard(strategy, maximum_cycles, title="Grandmaster FX Demo Dashboard")
        finally:
            gateway.close()
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@demo_app.command("stop")
def demo_stop() -> None:
    """Request a running demo worker to stop."""
    stop_path = Path("data/execution/demo/STOP")
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    console.print("Demo worker stop requested.")


@live_app.command("status")
def live_status(
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Display real live account and position state."""
    try:
        gateway, worker = _create_worker(
            ExecutionProfile.LIVE, strategy, timeframe, symbol, direction
        )
        try:
            gateway.account().require_real()
            console.print_json(data=worker.status())
        finally:
            gateway.close()
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@live_app.command("cycle")
def live_cycle(
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Run one real-money execution and signal-scanning cycle."""
    try:
        gateway, worker = _create_worker(
            ExecutionProfile.LIVE, strategy, timeframe, symbol, direction
        )
        try:
            gateway.account().require_real()
            console.print_json(data=worker.cycle())
        finally:
            gateway.close()
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@live_app.command("run")
def live_run(
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    maximum_cycles: int | None = None,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Continuously run the real-money execution manager."""
    try:
        gateway, worker = _create_worker(
            ExecutionProfile.LIVE, strategy, timeframe, symbol, direction
        )
        try:
            gateway.account().require_real()
            worker.run(maximum_cycles)
        finally:
            gateway.close()
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@live_app.command("dashboard")
def live_dashboard(
    strategy: str = "baseline_scalper",
    timeframe: Timeframe = Timeframe.M5,
    maximum_cycles: int | None = None,
    symbol: str | None = None,
    direction: TradeDirection = TradeDirection.ALL,
) -> None:
    """Run a continuously refreshing live execution dashboard."""
    try:
        gateway, worker = _create_worker(
            ExecutionProfile.LIVE, strategy, timeframe, symbol, direction
        )
        try:
            gateway.account().require_real()
            worker.run_dashboard(strategy, maximum_cycles, title="Grandmaster FX Live Dashboard")
        finally:
            gateway.close()
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


@live_app.command("stop")
def live_stop() -> None:
    """Request a running live worker to stop."""
    stop_path = Path("data/execution/live/STOP")
    stop_path.parent.mkdir(parents=True, exist_ok=True)
    stop_path.write_text(datetime.now(UTC).isoformat(), encoding="utf-8")
    console.print("Live worker stop requested.")


@predictions_app.command("config")
def predictions_config() -> None:
    """Display validated non-secret prediction configuration."""

    try:
        settings = load_prediction_settings()
        console.print_json(data=settings.model_dump(mode="json"))
    except GrandmasterFxError as error:
        _exit_with_error(error)


@predictions_app.command("inspect")
def predictions_inspect(
    pair: str,
    timeframe: Timeframe = Timeframe.M5,
    count: int = 200,
    strategy: str | None = None,
) -> None:
    """Inspect regime, strategy selection, and higher-timeframe confirmation."""
    from grandmaster_fx.predictions.regime import classify_regime

    try:
        prediction_settings = load_prediction_settings()
        symbol_settings = load_symbol_settings()
        experiments = load_experiment_settings()
        registry = _load_strategy_registry()
        manifests = {item.id: item for item in experiments.strategies if item.enabled}
        with Mt5Gateway(Mt5Secrets()) as gateway:
            gateway.account()
            service = MarketDataService(gateway, symbol_settings.symbols.allowed_currencies)
            name, primary_bars = service.bars(pair, timeframe, count)
            _higher_name, higher_bars = service.bars(
                pair,
                prediction_settings.confirmation.higher_timeframe,
                count,
            )
            metadata = gateway.symbol(name, symbol_settings.symbols.allowed_currencies)
            regime = classify_regime(primary_bars, prediction_settings.regime)
            selected_ids = prediction_settings.selection.strategies_for(regime.regime)
            if strategy is not None:
                if strategy not in manifests:
                    message = f"Unknown or disabled strategy: {strategy}"
                    raise ValueError(message)  # noqa: TRY301
                selected_ids = (strategy,)
            engine = PredictionEngine(prediction_settings)
            outcomes: list[dict[str, object]] = []
            for strategy_id in selected_ids:
                manifest = manifests.get(strategy_id)
                if manifest is None:
                    outcomes.append(
                        {
                            "strategy_id": strategy_id,
                            "available": False,
                            "accepted": False,
                            "reason": "manifest_missing_or_disabled",
                        }
                    )
                    continue
                implementation = registry.create(manifest)
                decision = implementation.evaluate(name, primary_bars, metadata.point)
                assessment = engine.assess(
                    strategy_id,
                    decision.signal,
                    primary_bars,
                    higher_bars,
                )
                outcomes.append(
                    {
                        "strategy_id": strategy_id,
                        "available": True,
                        "primary_signal": decision.signal.value,
                        "decision_reasons": [item.value for item in decision.reasons],
                        "strategy_allowed": assessment.strategy_allowed,
                        "confirmation": assessment.confirmation.confirmed,
                        "confirmation_reason": assessment.confirmation.reason.value,
                        "higher_fast_average": assessment.confirmation.fast_average,
                        "higher_slow_average": assessment.confirmation.slow_average,
                        "higher_momentum_percent": assessment.confirmation.momentum_percent,
                        "accepted": assessment.accepted,
                    }
                )
            report = {
                "symbol": name,
                "primary_timeframe": timeframe.value,
                "higher_timeframe": prediction_settings.confirmation.higher_timeframe.value,
                "regime": regime.regime.value,
                "trend_strength": regime.trend_strength,
                "volatility_ratio": regime.volatility_ratio,
                "efficiency_ratio": regime.efficiency_ratio,
                "selected_strategies": list(selected_ids),
                "outcomes": outcomes,
            }
            console.print_json(data=report)
    except (GrandmasterFxError, ValueError) as error:
        _exit_with_error(error)


def _exit_with_error(error: GrandmasterFxError | ValueError) -> None:
    console.print(f"[bold red]Error:[/bold red] {error}")
    raise typer.Exit(code=2) from error


def main() -> None:
    """Run the command-line application."""
    app()

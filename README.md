# Grandmaster FX

Grandmaster FX is a deterministic, configuration-driven forex research and execution system built around MetaTrader 5. It provides one command-line interface for market diagnostics, historical data, indicators, strategies, prediction gating, backtesting, robustness research, experiments, paper trading, demo execution, and isolated live execution.

> **Important:** Historical and simulated results do not guarantee future performance. Keep live execution in `dry_run = true` until the selected candidate has sufficient demo evidence and all operational checks pass.

## Core capabilities

- MetaTrader 5 terminal and account diagnostics
- Forex symbol discovery and broker suffix resolution
- Tick and completed-candle retrieval
- Technical indicator snapshots
- Multiple deterministic strategy implementations
- Chronological, no-lookahead backtesting
- Transaction-cost-aware trade simulation
- Market-regime classification
- Higher-timeframe prediction confirmation
- BUY, SELL, and ALL direction filters
- Holdout validation
- Anchored walk-forward testing
- Slippage and commission sensitivity testing
- Strategy experiment comparison
- Persistent paper trading
- MT5 demo execution
- Isolated live execution profile
- Dynamic Rich terminal dashboards
- Persistent journals, stop files, and consumed-signal state
- Ruff, mypy, pytest, and coverage quality gates

## Technology

- Python 3.12
- `uv` for Python and dependency management
- Typer for the CLI
- Rich for terminal dashboards and reports
- Pydantic for strict configuration validation
- MetaTrader 5 Python integration
- NumPy-based indicators
- pytest with a 90% coverage requirement

## Project structure

```text
configs/                         Validated TOML configuration
src/grandmaster_fx/
  backtesting/                   Chronological simulation engine
  config/                        Pydantic configuration models and loaders
  domain/                        Market, account, symbol, and execution models
  execution/                     Demo/live manager, worker, journal, dashboard
  experiments/                   Multi-strategy experiment framework
  indicators/                    Technical indicators
  infrastructure/                MT5 gateway and logging
  market_data/                   Symbol resolution and data service
  paper/                         Persistent simulated trading worker
  predictions/                   Regime, confirmation, direction, backtest gates
  research/                      Holdout, robustness, validation, exports
  strategies/                    Baseline and research strategies
tests/unit/                      Deterministic unit tests
data/                            Runtime state, journals, exports, reports
```

## Installation

Install Python 3.12 through `uv`:

```powershell
uv python install 3.12
```

Install locked dependencies:

```powershell
uv sync --locked
```

Show the CLI:

```powershell
uv run grandmaster-fx --help
```

Show the installed version:

```powershell
uv run grandmaster-fx --version
```

Run health checks:

```powershell
uv run grandmaster-fx doctor
```

Display the validated application configuration:

```powershell
uv run grandmaster-fx show-config
```

## Configuration

Main configuration files include:

```text
configs/app.toml
configs/backtest.toml
configs/risk.toml
configs/symbols.toml
configs/research.toml
configs/experiments.toml
configs/predictions.toml
configs/demo_execution.toml
configs/live_execution.toml
configs/strategies/*.toml
```

All configuration is strictly validated. Unknown fields and invalid values are rejected.

### Application execution mode

Use one execution profile at a time.

Demo profile:

```toml
[execution]
mode = "demo"
allow_live_account = false
```

Live profile validation:

```toml
[execution]
mode = "live"
allow_live_account = true
```

### Isolated execution profiles

Demo and live execution use separate operational resources:

```text
Demo configuration:  configs/demo_execution.toml
Live configuration:  configs/live_execution.toml

Demo magic:          771100
Live magic:          771101

Demo stop file:      data/execution/demo/STOP
Live stop file:      data/execution/live/STOP

Demo consumed state: data/execution/demo/consumed_predictions.json
Live consumed state: data/execution/live/consumed_predictions.json

Demo journal:        data/execution/demo/journal.jsonl
Live journal:        data/execution/live/journal.jsonl
```

Keep this setting enabled while validating the live profile without real submissions:

```toml
dry_run = true
```

Setting `dry_run = false` can allow accepted signals to reach the real-account order path when all other authorization, prediction, risk, and account checks pass.

## Prediction pipeline

The prediction pipeline performs:

1. Primary strategy evaluation on completed candles
2. Market-regime classification
3. Strategy eligibility for the detected regime
4. BUY, SELL, or ALL direction filtering
5. Higher-timeframe direction and momentum confirmation
6. Duplicate completed-candle rejection
7. Risk and execution checks

Supported regimes:

```text
trend
range
compression
high_volatility
uncertain
```

Default higher-timeframe confirmation is configured in `configs/predictions.toml`.

## Strategies

Available strategy IDs include:

```text
baseline_scalper
session_range_breakout
momentum_continuation
donchian_breakout
channel_mean_reversion
extreme_mean_reversion
fibonacci_pullback
volatility_expansion
volatility_expansion_window
```

List and inspect experiment configuration before selecting a strategy:

```powershell
uv run grandmaster-fx experiments --help
uv run grandmaster-fx predictions config
```

## Candidate currently under observation

The current research candidate is:

```text
Symbol:           USDJPY
Primary timeframe: M5
Strategy:         momentum_continuation
Direction:        BUY only
Prediction gates: enabled
```

Run it on the demo dashboard:

```powershell
uv run grandmaster-fx demo dashboard `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

## Backtesting

Prediction-gated BUY-only backtest:

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

Raw comparison:

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --no-predictions
```

The report includes trades, return, drawdown, win rate, profit factor, expectancy, losing streak, and prediction rejection diagnostics.

## Research validation

Chronological holdout validation:

```powershell
uv run grandmaster-fx research validate `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

Walk-forward and cost sensitivity:

```powershell
uv run grandmaster-fx research robustness `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

## Paper trading

Paper trading uses persistent simulated positions and does not place MT5 orders.

```powershell
uv run grandmaster-fx paper status `
  --symbol USDJPY `
  --direction BUY
```

```powershell
uv run grandmaster-fx paper cycle `
  --symbol USDJPY `
  --direction BUY
```

```powershell
uv run grandmaster-fx paper run `
  --symbol USDJPY `
  --direction BUY
```

Stop the paper worker:

```powershell
uv run grandmaster-fx paper stop
```

The paper worker uses its own simulated signal logic. Use the demo worker to observe the exact prediction-gated MT5 candidate.

## Demo execution

Set `configs/app.toml` to demo mode and connect MetaTrader 5 to a demo account.

Status:

```powershell
uv run grandmaster-fx demo status `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Single cycle:

```powershell
uv run grandmaster-fx demo cycle `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Continuous JSON worker:

```powershell
uv run grandmaster-fx demo run `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Dynamic dashboard:

```powershell
uv run grandmaster-fx demo dashboard `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Stop:

```powershell
uv run grandmaster-fx demo stop
```

## Live execution profile

Set `configs/app.toml` to live mode, connect MetaTrader 5 to a real account, and keep `dry_run = true` while validating isolation and output.

Status:

```powershell
uv run grandmaster-fx live status `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Single cycle:

```powershell
uv run grandmaster-fx live cycle `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Continuous JSON worker:

```powershell
uv run grandmaster-fx live run `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Dynamic dashboard:

```powershell
uv run grandmaster-fx live dashboard `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Stop:

```powershell
uv run grandmaster-fx live stop
```

Live commands require a real account and the matching live execution profile.

## Dashboard interpretation

A prediction becomes eligible only when the row effectively shows:

```text
Signal:            BUY or SELL
Strategy allowed:  YES
Direction allowed: YES
HTF confirmation:  YES
Duplicate:         NO
Accepted:          ACCEPT
```

Common reasons:

```text
outside_session        Current candle is outside the strategy's trading hours.
breakout_not_confirmed Price has not completed a valid range breakout.
buy_setup_confirmed    Primary BUY conditions passed.
sell_setup_confirmed   Primary SELL conditions passed.
trend_not_aligned      Required trend or price alignment is absent.
hold_signal            Primary strategy returned HOLD, so HTF confirmation was skipped.
direction_mismatch     Higher timeframe disagrees with the primary signal.
momentum_too_weak      Higher-timeframe movement is below the configured threshold.
strategy_not_allowed   Strategy is not enabled for the detected regime.
regime_mismatch        Confirmation rules reject the current regime.
```

## Quality gates

Format:

```powershell
uv run ruff format .
```

Lint:

```powershell
uv run ruff check .
```

Type check:

```powershell
uv run mypy
```

Tests:

```powershell
uv run pytest
```

Coverage:

```powershell
uv run pytest `
  --cov=grandmaster_fx `
  --cov-report=term-missing
```

The project requires at least 90% coverage.

## Operational notes

- Strategies evaluate completed candles, not every polling cycle as a new opportunity.
- Hundreds of worker cycles may repeatedly evaluate the same M5 candle.
- Do not tune settings in response to a few minutes of observation.
- Preserve journals and consumed-signal state when investigating unusual behavior.
- Use `Ctrl+C` to leave a dashboard.
- Use the corresponding `stop` command to stop a background worker.
- Demo and live stop files, journals, consumed signals, and magic numbers are isolated.

## Additional command documentation

See [RUNBOOK.md](RUNBOOK.md) for the complete operator command guide.

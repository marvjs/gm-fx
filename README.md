# Grandmaster FX

Grandmaster FX is a configuration-driven MetaTrader 5 research and execution platform. It provides completed-candle analysis, deterministic strategies, prediction gates, historical backtesting, robustness research, paper simulation, isolated demo and live execution profiles, and a complete pending-order lifecycle.

> **Risk warning:** Forex trading can cause financial loss. A passing test suite, profitable backtest, demo result, or broker-validated request does not guarantee future performance. Use paper and demo modes first. Keep live execution in dry-run until the account, strategy, risk configuration, broker constraints, and operational procedures have been independently reviewed.

## Current production baseline

```text
Application:       Grandmaster FX
Version:           1.13.7
Python:            3.12.x
Environment:       uv
MT5 platform:      Windows
Automated tests:   294 passing
Coverage gate:     90% minimum
```

## What the system does

Grandmaster FX separates trading into explicit gates:

```text
MT5 and configuration gate
→ Market-data quality gate
→ Strategy gate
→ Direction gate
→ Optional prediction gate
→ Risk gate
→ Execution-profile gate
→ Pending-order gate when selected
→ Broker validation and confirmation
→ Journal and reconciliation
```

A failure at any gate prevents the next stage. A HOLD result is not an error. It means no acceptable opportunity exists on the last completed candle.

## Main capabilities

### Market data

- Connects to the official MetaTrader 5 Python interface.
- Discovers broker-specific symbols, including suffixes such as `USDJPYm`.
- Retrieves ticks and completed UTC candles.
- Validates ordering, duplication, gaps, and freshness.
- Exports candles to CSV.
- Caches exact research requests locally.

### Strategies

Nine deterministic strategies are available:

1. `baseline_scalper`
2. `channel_mean_reversion`
3. `donchian_breakout`
4. `extreme_mean_reversion`
5. `fibonacci_pullback`
6. `momentum_continuation`
7. `session_range_breakout`
8. `volatility_expansion`
9. `volatility_expansion_window`

There is no universally “best” strategy. The correct choice depends on symbol, timeframe, regime, direction, costs, and out-of-sample evidence. See [Strategy Guide](docs/04_STRATEGIES.md).

### Prediction gates

Commands that support:

```text
--predictions / --no-predictions
```

can either apply or bypass the prediction layer.

- `--predictions` keeps the strategy signal only when regime eligibility, direction confirmation, and momentum confirmation pass.
- `--no-predictions` uses the raw strategy decision after the ordinary direction filter.

Predictions do not forecast a guaranteed future price. They are deterministic filters that reduce the number of raw strategy signals. See [Prediction Gate](docs/05_PREDICTIONS_GATE.md).

### Research

- Standard chronological backtesting
- Prediction-gated and raw comparisons
- Holdout validation
- Anchored walk-forward analysis
- Cost-sensitivity analysis
- Strategy comparison experiments
- Pending-entry historical simulation

### Execution profiles

- **Paper:** local broker-free state and pending lifecycle
- **Demo:** isolated MT5 demo account, magic, journal, stop file, and consumed-signal state
- **Live:** isolated MT5 real account, separate magic and runtime state, dry-run support, broker confirmation, and reconciliation

### Pending orders

- Inspect plans without placing orders
- Historical pending-entry backtesting
- Paper pending placement and bar-by-bar reconciliation
- Demo pending placement, listing, reconciliation, and cancellation
- Live request validation and authorized placement
- Post-submission ticket confirmation
- Persistent identity-to-ticket ownership registry
- Active order, position, order-history, and deal-history reconciliation

## Documentation map

### Start here

- [Installation](docs/01_INSTALLATION.md)
- [System Concepts and Gates](docs/02_SYSTEM_GATES.md)
- [Command Reference](docs/03_COMMAND_REFERENCE.md)
- [Strategy Guide](docs/04_STRATEGIES.md)
- [Prediction Gate](docs/05_PREDICTIONS_GATE.md)
- [Configuration Reference](docs/06_CONFIGURATION.md)

### Research and execution gates

- [Market Data Gate](docs/07_MARKET_DATA_GATE.md)
- [Backtest and Research Gate](docs/08_RESEARCH_GATE.md)
- [Pending Order Gate](docs/09_PENDING_GATE.md)
- [Paper Gate](docs/10_PAPER_GATE.md)
- [Demo Gate](docs/11_DEMO_GATE.md)
- [Live Gate](docs/12_LIVE_GATE.md)
- [Risk Gate](docs/13_RISK_GATE.md)
- [Observability and Reconciliation](docs/14_OBSERVABILITY.md)

### Operator documents

- [Demo Quick Start](docs/15_DEMO_QUICKSTART.md)
- [Live Quick Start](docs/16_LIVE_QUICKSTART.md)
- [Troubleshooting](docs/17_TROUBLESHOOTING.md)
- [Testing and Release Gate](docs/18_TESTING_RELEASE.md)
- [Operations Runbook](RUNBOOK.md)

## Installation summary

```powershell
uv python install 3.12
uv sync --locked
uv run grandmaster-fx --version
uv run grandmaster-fx --help
```

Open MetaTrader 5 and sign in, then run:

```powershell
uv run grandmaster-fx mt5 doctor
uv run grandmaster-fx mt5 terminal
uv run grandmaster-fx mt5 account
```

## Typical research command

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

Compare it with the raw strategy:

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --no-predictions
```

Do not choose a strategy from one backtest. Compare raw and prediction-gated results, test more than one date range, use holdout and walk-forward evidence, and include realistic costs.

## Typical pending workflow

```powershell
uv run grandmaster-fx pending inspect `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --direction BUY `
  --predictions

uv run grandmaster-fx pending backtest `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

Then move through the gates in order:

```text
Historical research
→ Paper pending lifecycle
→ MT5 demo pending lifecycle
→ Live dry-run validation
→ Separately authorized live operation
```

## Quality gate

```powershell
uv run ruff format .
uv run ruff check --fix .
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest `
  --cov=grandmaster_fx `
  --cov-report=term-missing
```

Expected baseline:

```text
294 tests passed
Coverage at or above 90%
```

## Runtime ownership

```text
Demo magic: 771100
Live magic: 771101
```

Important runtime files:

```text
data/paper/state.json
data/paper/pending_orders.json
data/execution/demo/journal.jsonl
data/execution/demo/consumed_predictions.json
data/execution/live/journal.jsonl
data/execution/live/consumed_predictions.json
data/execution/live/pending_orders.json
logs/grandmaster-fx.log
```

Do not manually edit live ownership state during an incident. Back it up and reconcile it against MetaTrader 5 first.

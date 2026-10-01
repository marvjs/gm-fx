# Grandmaster FX Runbook

This runbook is the command guide for installing, validating, researching, and operating Grandmaster FX.

## 1. Shell preparation

Open PowerShell and enter the project:

```powershell
Set-Location "C:\path\to\grandmaster-fx"
```

Install Python and dependencies:

```powershell
uv python install 3.12
uv sync --locked
```

Check the CLI:

```powershell
uv run grandmaster-fx --help
uv run grandmaster-fx --version
```

## 2. Preflight checklist

Run before research or worker execution:

```powershell
uv run grandmaster-fx doctor
uv run grandmaster-fx show-config
```

Inspect command groups:

```powershell
uv run grandmaster-fx mt5 --help
uv run grandmaster-fx symbols --help
uv run grandmaster-fx data --help
uv run grandmaster-fx indicators --help
uv run grandmaster-fx strategy --help
uv run grandmaster-fx backtest --help
uv run grandmaster-fx research --help
uv run grandmaster-fx experiments --help
uv run grandmaster-fx predictions --help
uv run grandmaster-fx paper --help
uv run grandmaster-fx demo --help
uv run grandmaster-fx live --help
```

## 3. MetaTrader 5 diagnostics

Validate the terminal, account, and complete MT5 connection report:

```powershell
uv run grandmaster-fx mt5 doctor
uv run grandmaster-fx mt5 terminal
uv run grandmaster-fx mt5 account
```

If a command name differs in the installed build, inspect the group first:

```powershell
uv run grandmaster-fx mt5 --help
```

## 4. Symbol discovery

List supported forex symbols:

```powershell
uv run grandmaster-fx symbols list
```

Inspect or validate a pair:

```powershell
uv run grandmaster-fx symbols inspect USDJPY
uv run grandmaster-fx symbols validate USDJPY
```

Broker suffixes are resolved automatically, for example `USDJPY` to `USDJPYm`.

Use the installed help if exact subcommand names differ:

```powershell
uv run grandmaster-fx symbols --help
```

## 5. Market data

Display the latest tick:

```powershell
uv run grandmaster-fx data tick USDJPY
```

Retrieve completed bars:

```powershell
uv run grandmaster-fx data bars `
  USDJPY `
  --timeframe M5 `
  --count 500
```

Export bars:

```powershell
uv run grandmaster-fx data export `
  USDJPY `
  --timeframe M5 `
  --count 10000
```

Inspect available data commands:

```powershell
uv run grandmaster-fx data --help
```

## 6. Indicators and primary strategy

Display the latest indicator snapshot:

```powershell
uv run grandmaster-fx indicators snapshot `
  USDJPY `
  --timeframe M5
```

Inspect a strategy decision:

```powershell
uv run grandmaster-fx strategy inspect `
  USDJPY `
  --timeframe M5
```

## 7. Prediction inspection

Display prediction configuration:

```powershell
uv run grandmaster-fx predictions config
```

Inspect all regime-selected strategies:

```powershell
uv run grandmaster-fx predictions inspect `
  USDJPY `
  --timeframe M5
```

Inspect one strategy:

```powershell
uv run grandmaster-fx predictions inspect `
  USDJPY `
  --timeframe M5 `
  --strategy momentum_continuation
```

Inspect several pairs:

```powershell
$Pairs = @("EURUSD", "GBPUSD", "USDJPY")

foreach ($Pair in $Pairs) {
  Write-Host "`n===== $Pair =====" -ForegroundColor Cyan

  uv run grandmaster-fx predictions inspect `
    $Pair `
    --timeframe M5
}
```

## 8. Backtesting

### Exact BUY-only candidate

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

### Raw strategy comparison

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --no-predictions
```

### SELL-only comparison

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction SELL `
  --predictions
```

### Pair and strategy comparison loop

```powershell
$Pairs = @("EURUSD", "GBPUSD", "USDJPY")
$Strategies = @(
  "channel_mean_reversion",
  "session_range_breakout",
  "momentum_continuation"
)

foreach ($Pair in $Pairs) {
  foreach ($Strategy in $Strategies) {
    Write-Host "`n===== $Pair | $Strategy | RAW =====" -ForegroundColor Cyan

    uv run grandmaster-fx backtest run `
      $Pair `
      --strategy $Strategy `
      --timeframe M5 `
      --count 10000 `
      --no-predictions

    Write-Host "`n===== $Pair | $Strategy | GATED =====" -ForegroundColor Yellow

    uv run grandmaster-fx backtest run `
      $Pair `
      --strategy $Strategy `
      --timeframe M5 `
      --count 10000 `
      --predictions
  }
}
```

## 9. Holdout validation

Prediction-gated BUY-only validation:

```powershell
uv run grandmaster-fx research validate `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

Raw validation:

```powershell
uv run grandmaster-fx research validate `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --no-predictions
```

Review:

```text
PASS or FAIL
Trade count
Return
Maximum drawdown
Profit factor
Expectancy
Costs
Warnings
Prediction rejection counts
```

## 10. Walk-forward and cost sensitivity

```powershell
uv run grandmaster-fx research robustness `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

Raw comparison:

```powershell
uv run grandmaster-fx research robustness `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --no-predictions
```

Review:

```text
STABLE or UNSTABLE
Profitable folds
Per-fold returns
Per-fold drawdowns
Per-fold profit factors
Slippage sensitivity
Commission sensitivity
BUY and SELL ablations
Holding-duration ablations
```

## 11. Experiments

Show experiment commands:

```powershell
uv run grandmaster-fx experiments --help
```

Run a quick comparison:

```powershell
uv run grandmaster-fx experiments compare `
  USDJPY `
  --timeframe M5 `
  --count 10000 `
  --mode quick
```

Run full comparison:

```powershell
uv run grandmaster-fx experiments compare `
  USDJPY `
  --timeframe M5 `
  --count 20000 `
  --mode full
```

Use `--strategy` when you want one registered strategy and the installed command supports it. Use `--help` to inspect exact options.

## 12. Paper worker

Status:

```powershell
uv run grandmaster-fx paper status `
  --symbol USDJPY `
  --direction BUY
```

Single cycle:

```powershell
uv run grandmaster-fx paper cycle `
  --symbol USDJPY `
  --direction BUY
```

Continuous run:

```powershell
uv run grandmaster-fx paper run `
  --symbol USDJPY `
  --direction BUY
```

Stop:

```powershell
uv run grandmaster-fx paper stop
```

Use `Ctrl+C` to stop an attached process immediately.

## 13. Demo execution

### Configure demo profile

Edit `configs/app.toml`:

```toml
[execution]
mode = "demo"
allow_live_account = false
```

Confirm MetaTrader 5 is connected to a demo account.

### Status

```powershell
uv run grandmaster-fx demo status `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### One cycle

```powershell
uv run grandmaster-fx demo cycle `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Continuous JSON output

```powershell
uv run grandmaster-fx demo run `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Dynamic dashboard

```powershell
uv run grandmaster-fx demo dashboard `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Stop

```powershell
uv run grandmaster-fx demo stop
```

Demo runtime files:

```text
data/execution/demo/STOP
data/execution/demo/consumed_predictions.json
data/execution/demo/journal.jsonl
```

## 14. Live profile validation

### Configure live profile

Edit `configs/app.toml`:

```toml
[execution]
mode = "live"
allow_live_account = true
```

Keep `configs/live_execution.toml` in dry-run mode while checking identity and isolation:

```toml
[execution]
dry_run = true
magic = 771101
comment = "grandmaster-fx-live"
```

Confirm MetaTrader 5 is connected to the intended real account.

### Status

```powershell
uv run grandmaster-fx live status `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### One cycle

```powershell
uv run grandmaster-fx live cycle `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Continuous JSON worker

```powershell
uv run grandmaster-fx live run `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Dynamic dashboard

```powershell
uv run grandmaster-fx live dashboard `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Stop

```powershell
uv run grandmaster-fx live stop
```

Live runtime files:

```text
data/execution/live/STOP
data/execution/live/consumed_predictions.json
data/execution/live/journal.jsonl
```

### Before changing dry-run

Verify all of the following:

```text
profile = live
account_mode = REAL
magic = 771101
comment = grandmaster-fx-live
symbol = USDJPY broker resolution
direction = BUY
stop path points to data/execution/live
consumed path points to data/execution/live
journal path points to data/execution/live
terminal connected = true
account trade allowed = true
expert trade allowed = true
trade API enabled = true
```

Setting `dry_run = false` can allow actual broker submissions when an accepted signal and all checks pass.

## 15. Dashboard controls

Leave a dashboard with:

```text
Ctrl+C
```

Stop it from another terminal with the matching command:

```powershell
uv run grandmaster-fx demo stop
```

or:

```powershell
uv run grandmaster-fx live stop
```

Do not use the demo stop command for live or the live stop command for demo.

## 16. Runtime file inspection

Inspect all execution state:

```powershell
Get-ChildItem .\data\execution -Recurse
```

Inspect demo journal:

```powershell
Get-Content .\data\execution\demo\journal.jsonl -Tail 50
```

Inspect live journal:

```powershell
Get-Content .\data\execution\live\journal.jsonl -Tail 50
```

Inspect consumed demo predictions:

```powershell
Get-Content .\data\execution\demo\consumed_predictions.json
```

Inspect consumed live predictions:

```powershell
Get-Content .\data\execution\live\consumed_predictions.json
```

## 17. Quality validation

Format:

```powershell
uv run ruff format .
```

Check formatting:

```powershell
uv run ruff format --check .
```

Lint:

```powershell
uv run ruff check .
```

Type check:

```powershell
uv run mypy
```

Focused tests:

```powershell
uv run pytest `
  tests/unit/test_execution_isolation.py `
  tests/unit/test_candidate_filters.py `
  tests/unit/test_prediction_worker.py `
  tests/unit/test_prediction_backtest.py `
  tests/unit/test_prediction_research_cli.py `
  -vv
```

Full suite:

```powershell
uv run pytest
```

Coverage:

```powershell
uv run pytest `
  --cov=grandmaster_fx `
  --cov-report=term-missing
```

Expected quality outcome:

```text
Ruff format: clean
Ruff check: clean
mypy: success
pytest: all tests pass
coverage: at least 90%
```

## 18. Troubleshooting

### `outside_session`

The strategy is outside its configured UTC trading window. Wait for the configured session or use a strategy appropriate for the current regime.

### `trend_not_aligned`

The strategy cannot confirm the required trend, price location, or reversal alignment. No entry should be created.

### `hold_signal`

The primary strategy returned HOLD. Higher-timeframe confirmation was skipped.

### `direction_mismatch`

The higher timeframe moves against the primary BUY or SELL signal.

### `momentum_too_weak`

The higher-timeframe move is in the expected direction but below the configured minimum.

### `strategy_not_allowed`

The strategy is not mapped to the detected regime.

### `duplicate = true`

The same completed-candle signal has already been consumed by that execution profile.

### No positions after many cycles

Polling cycles are not independent trading opportunities. M5 produces one new completed candle approximately every five minutes. Hundreds of cycles can repeatedly inspect the same candle.

### Wrong execution mode

Set `configs/app.toml` to the matching profile:

```text
demo command -> mode = "demo"
live command -> mode = "live"
```

### Live command rejects the account

Live commands require a real MT5 account. Demo and contest accounts are rejected.

### Coverage below 90%

Do not lower the threshold. Add focused tests for the newly introduced branches.

### Worker shows an evaluation error

Read the `error` field in cycle output and inspect the correct profile journal. Evaluation errors are retained instead of silently dropping the symbol.

## 19. Recommended daily workflow

### Research day

```powershell
uv run grandmaster-fx doctor
uv run grandmaster-fx predictions inspect USDJPY --timeframe M5 --strategy momentum_continuation
uv run grandmaster-fx backtest run USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
uv run grandmaster-fx research validate USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
uv run grandmaster-fx research robustness USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
```

### Demo observation day

```powershell
uv run grandmaster-fx doctor
uv run grandmaster-fx demo status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo dashboard --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
```

### Live-profile validation day

Keep `dry_run = true`:

```powershell
uv run grandmaster-fx doctor
uv run grandmaster-fx live status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx live cycle --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx live dashboard --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
```

## 20. Backup before changes

Create a project backup:

```powershell
Compress-Archive `
  -Path .\* `
  -DestinationPath "..\grandmaster-fx-backup.zip" `
  -Force
```

Create a Git checkpoint:

```powershell
git add .
git commit -m "Checkpoint Grandmaster FX"
git status
```

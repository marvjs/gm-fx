# Grandmaster FX Quick Start

Use this guide to run the current candidate in demo mode or validate the live profile using the dashboard.

## Current candidate

```text
Symbol: USDJPY
Strategy: momentum_continuation
Timeframe: M5
Direction: BUY only
Prediction gates: enabled
Higher-timeframe confirmation: configured in configs/predictions.toml
```

## 1. Open the project

```powershell
Set-Location "C:\Users\kimo\Desktop\Automarv\grandmaster-fx"
uv sync --locked
```

## 2. Run a health check

Make sure MetaTrader 5 is open and connected to the intended account.

```powershell
uv run grandmaster-fx doctor
```

## 3. Demo quick start

Edit `configs/app.toml`:

```toml
[execution]
mode = "demo"
allow_live_account = false
```

Make sure MetaTrader 5 is connected to a demo account.

### Run one demo cycle

```powershell
uv run grandmaster-fx demo cycle `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Start the demo dashboard

```powershell
uv run grandmaster-fx demo dashboard `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Stop demo execution

Press `Ctrl+C` in the dashboard terminal, or run this from another terminal:

```powershell
uv run grandmaster-fx demo stop
```

## 4. Live-profile quick start

> Keep `dry_run = true` while validating the live profile. Setting it to `false` may allow accepted signals to reach real-account order submission.

Edit `configs/app.toml`:

```toml
[execution]
mode = "live"
allow_live_account = true
```

Confirm `configs/live_execution.toml` contains:

```toml
[execution]
dry_run = true
magic = 771101
comment = "grandmaster-fx-live"
```

Make sure MetaTrader 5 is connected to the intended real account.

### Check live-profile status

```powershell
uv run grandmaster-fx live status `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

Confirm the output identifies:

```text
Profile: live
Account mode: REAL
Magic: 771101
Comment: grandmaster-fx-live
Symbol: USDJPY or the resolved broker symbol
Direction: BUY
Stop path: data/execution/live/STOP
Consumed state: data/execution/live/consumed_predictions.json
```

### Run one live-profile cycle

```powershell
uv run grandmaster-fx live cycle `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Start the live dashboard

```powershell
uv run grandmaster-fx live dashboard `
  --strategy momentum_continuation `
  --timeframe M5 `
  --symbol USDJPY `
  --direction BUY
```

### Stop the live worker

Press `Ctrl+C` in the dashboard terminal, or run this from another terminal:

```powershell
uv run grandmaster-fx live stop
```

## 5. What to watch on the dashboard

A prediction is eligible only when the row shows the equivalent of:

```text
Signal: BUY
Strategy allowed: YES
Direction allowed: YES
Higher-timeframe confirmation: YES
Duplicate: NO
Accepted: ACCEPT
```

Common waiting states:

```text
HOLD                 No primary entry signal
trend_not_aligned    Strategy conditions are incomplete
strategy_not_allowed Current regime does not allow the strategy
direction_mismatch   Higher timeframe disagrees
a momentum warning  Higher-timeframe movement is too weak
duplicate            Signal was already consumed
```

## 6. Quick research check

Run the current BUY-only prediction-gated backtest:

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

Run walk-forward and cost-sensitivity research:

```powershell
uv run grandmaster-fx research robustness `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

## 7. Runtime files

```text
Demo journal:        data/execution/demo/journal.jsonl
Demo consumed state: data/execution/demo/consumed_predictions.json
Demo stop file:      data/execution/demo/STOP

Live journal:        data/execution/live/journal.jsonl
Live consumed state: data/execution/live/consumed_predictions.json
Live stop file:      data/execution/live/STOP
```

Inspect the active journal:

```powershell
Get-Content .\data\execution\demo\journal.jsonl -Tail 30
```

or:

```powershell
Get-Content .\data\execution\live\journal.jsonl -Tail 30
```

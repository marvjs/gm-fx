# Command Reference

Use `uv run grandmaster-fx <group> --help` as the authoritative source for the exact installed build. This guide explains the purpose and common options.

## Root commands

```powershell
uv run grandmaster-fx --version
uv run grandmaster-fx --help
uv run grandmaster-fx doctor
uv run grandmaster-fx show-config
```

- `doctor`: foundational configuration and MT5 safety diagnostics.
- `show-config`: prints the validated application configuration.

## Common analysis options

### `PAIR` or `--symbol`

A currency pair such as `USDJPY`. The resolver may map it to a broker-specific symbol such as `USDJPYm`.

### `--strategy`

Selects one of the nine registered strategy identifiers. It does not mean there is only one strategy. See `04_STRATEGIES.md`.

### `--timeframe`

Selects the candle timeframe, for example `M1`, `M5`, `M15`, `M30`, `H1`, or another timeframe supported by the project and broker.

### `--count`

Number of completed candles requested. Larger research counts increase historical coverage but may take longer and depend on broker history availability.

### `--direction`

```text
ALL  Accept BUY and SELL
BUY  Accept BUY only
SELL Accept SELL only
```

### `--predictions / --no-predictions`

- `--predictions`: apply regime eligibility and higher-timeframe confirmation after the raw strategy signal.
- `--no-predictions`: bypass those extra filters and use the raw strategy decision.

Always compare both versions during research.

## `mt5`

```powershell
uv run grandmaster-fx mt5 doctor
uv run grandmaster-fx mt5 terminal
uv run grandmaster-fx mt5 account
```

- `doctor`: connection diagnostics.
- `terminal`: terminal connection and trading flags.
- `account`: account number, server, mode, balance, equity, and permissions.

## `symbols`

```powershell
uv run grandmaster-fx symbols list
uv run grandmaster-fx symbols inspect USDJPY
uv run grandmaster-fx symbols validate USDJPY EURUSD GBPUSD
```

- `list`: currency symbols available through the broker.
- `inspect`: resolved broker symbol and trading properties.
- `validate`: checks a set of configured pairs.

## `data`

```powershell
uv run grandmaster-fx data tick USDJPY
uv run grandmaster-fx data bars USDJPY --timeframe M5 --count 500
uv run grandmaster-fx data export USDJPY --timeframe M5 --count 10000
```

- `tick`: latest bid/ask snapshot.
- `bars`: completed candle retrieval.
- `export`: writes validated candles to CSV.

## `indicators`

```powershell
uv run grandmaster-fx indicators inspect USDJPY --timeframe M5 --count 200
```

Calculates the indicator snapshot used by strategies and diagnostics.

## `strategy`

```powershell
uv run grandmaster-fx strategy inspect USDJPY --timeframe M5 --count 200
```

Inspects the baseline strategy path. For named registered strategies, use commands that accept `--strategy`.

## `predictions`

```powershell
uv run grandmaster-fx predictions config
uv run grandmaster-fx predictions inspect USDJPY --strategy momentum_continuation --timeframe M5
```

- `config`: prints prediction configuration.
- `inspect`: shows raw strategy decision, regime, eligibility, confirmation decision, and final acceptance.

## `backtest`

```powershell
uv run grandmaster-fx backtest run `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

Options select symbol, strategy, timeframe, history size, allowed direction, and whether prediction gates apply.

## `research`

```powershell
uv run grandmaster-fx research validate ...
uv run grandmaster-fx research robustness ...
```

- `validate`: chronological holdout validation.
- `robustness`: walk-forward, cost sensitivity, and configured robustness checks.

Use the same common analysis options as backtesting.

## `experiments`

```powershell
uv run grandmaster-fx experiments compare USDJPY --timeframe M5 --count 10000 --mode quick
uv run grandmaster-fx experiments compare USDJPY --timeframe M5 --count 20000 --mode full
```

- `quick`: faster comparison.
- `full`: more complete evidence and robustness processing.

## `pending`

```powershell
uv run grandmaster-fx pending inspect `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 200 `
  --direction BUY `
  --predictions
```

```powershell
uv run grandmaster-fx pending backtest `
  USDJPY `
  --strategy momentum_continuation `
  --timeframe M5 `
  --count 20000 `
  --direction BUY `
  --predictions
```

- `inspect`: creates and prints a plan only.
- `backtest`: historical pending trigger, expiration, and trade simulation.

## `paper`

```powershell
uv run grandmaster-fx paper status --symbol USDJPY --direction BUY
uv run grandmaster-fx paper cycle --symbol USDJPY --direction BUY
uv run grandmaster-fx paper run --symbol USDJPY --direction BUY
uv run grandmaster-fx paper run --maximum-cycles 10 --symbol USDJPY --direction BUY
uv run grandmaster-fx paper stop
```

Pending commands:

```powershell
uv run grandmaster-fx paper pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
uv run grandmaster-fx paper pending-list
uv run grandmaster-fx paper pending-reconcile
```

## `demo`

```powershell
uv run grandmaster-fx demo status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo cycle --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo run --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo dashboard --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo stop
```

Pending commands:

```powershell
uv run grandmaster-fx demo pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
uv run grandmaster-fx demo pending-list
uv run grandmaster-fx demo pending-reconcile
uv run grandmaster-fx demo pending-cancel 12345678
```

## `live`

The live group mirrors the demo worker but requires the live profile and a real account.

```powershell
uv run grandmaster-fx live status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx live cycle --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx live run --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx live dashboard --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx live stop
```

Pending commands:

```powershell
uv run grandmaster-fx live pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
uv run grandmaster-fx live pending-list
uv run grandmaster-fx live pending-reconcile
uv run grandmaster-fx live pending-cancel 12345678
```

Keep `dry_run = true` until separately authorized.

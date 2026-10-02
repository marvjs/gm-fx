# Demo Gate

## Authorization

```toml
# configs/app.toml
[execution]
mode = "demo"
allow_live_account = false
```

The connected MT5 account must be demo mode.

## Isolation

```text
Magic:          771100
Profile paths:  data/execution/demo/
```

## Status

```powershell
uv run grandmaster-fx demo status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
```

Check terminal connection, trading permission, expert permission, API state, account mode, magic, and runtime paths.

## Worker

```powershell
uv run grandmaster-fx demo cycle --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo run --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo dashboard --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo stop
```

## Pending lifecycle

```powershell
uv run grandmaster-fx demo pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
uv run grandmaster-fx demo pending-list
uv run grandmaster-fx demo pending-reconcile
uv run grandmaster-fx demo pending-cancel 12345678
```

Only cancel a ticket returned under the demo magic. A HOLD result creates no pending order.

# Paper Gate

## Purpose

Exercise strategy and pending lifecycle without sending broker-changing requests.

## Worker commands

```powershell
uv run grandmaster-fx paper status --symbol USDJPY --direction BUY
uv run grandmaster-fx paper cycle --symbol USDJPY --direction BUY
uv run grandmaster-fx paper run --symbol USDJPY --direction BUY
uv run grandmaster-fx paper run --maximum-cycles 10 --symbol USDJPY --direction BUY
uv run grandmaster-fx paper stop
```

## Pending commands

```powershell
uv run grandmaster-fx paper pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
uv run grandmaster-fx paper pending-list
uv run grandmaster-fx paper pending-reconcile
```

## State

```text
data/paper/state.json
data/paper/pending_orders.json
data/paper/STOP
```

Paper testing validates lifecycle logic, restart persistence, and strategy frequency. It does not validate broker rejection codes, fill policy, slippage, freezes, or server-side expiration.

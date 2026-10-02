# Pending Order Gate

## Purpose

Convert an accepted directional strategy decision into a future broker entry instead of entering immediately at market.

## Plan fields

```text
identity
strategy_id
symbol
timeframe
signal
order_type
source_time
trigger_price
stop_loss
take_profit
maximum_wait_bars
score
```

## Order types

- BUY STOP: trigger above current ask
- SELL STOP: trigger below current bid
- BUY LIMIT: trigger below current ask
- SELL LIMIT: trigger above current bid

The supplied configuration primarily uses stop entries. Support in the model does not mean every broker or current configuration permits every type.

## Inspect

```powershell
uv run grandmaster-fx pending inspect USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
```

No order is submitted.

## Backtest

```powershell
uv run grandmaster-fx pending backtest USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
```

Additional metrics:

```text
plans_created
plans_triggered
plans_expired
average_wait_bars
trigger_rate_percent
expiration_rate_percent
```

## Duplicate behavior

Equivalent active orders are retained according to the replacement policy. This prevents repeated polling from creating duplicate exposure.

## Expiration

`maximum_wait_bars` is expressed in completed bars. Three M5 bars represent approximately fifteen minutes of candle time, subject to session closures and broker behavior.

## Profile commands

```powershell
uv run grandmaster-fx paper pending-place ...
uv run grandmaster-fx demo pending-place ...
uv run grandmaster-fx live pending-place ...
```

Each profile has separate ownership and state.

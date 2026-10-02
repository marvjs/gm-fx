# Live Gate

## Authorization

```toml
# configs/app.toml
[execution]
mode = "live"
allow_live_account = true
```

```toml
# configs/live_execution.toml
[execution]
enabled = true
dry_run = true
magic = 771101
comment = "grandmaster-fx-live"
```

The connected account must be real mode.

## Dry-run meaning

With `dry_run = true`, the system may perform strategy analysis, prediction checks, duplicate lookup, risk sizing, request construction, and broker `order_check`, but it must not submit the pending order.

## Live status

```powershell
uv run grandmaster-fx live status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
```

## Live pending validation

```powershell
uv run grandmaster-fx live pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
```

Expected dry-run result:

```json
{
  "placed": false,
  "validated": true,
  "reason": "dry_run_pending_plan_validated",
  "ticket": null
}
```

## Confirmation

When separately authorized submission is enabled, the returned ticket must be found again in active broker orders. The broker snapshot is compared with symbol, direction, type, trigger, stop, target, and volume.

## Registry

```text
data/execution/live/pending_orders.json
```

States:

```text
active
triggered
filled
canceled
expired
rejected
externally_modified
missing
unknown
```

## Reconcile before retry

If result is `broker_confirmation_missing`, do not blindly place again:

```powershell
uv run grandmaster-fx live pending-list
uv run grandmaster-fx live pending-reconcile
```

Then inspect MT5 and the live journal.

# Live Quick Start

This quick start intentionally keeps live pending execution in dry-run.

## 1. Configure live mode

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

## 2. Connect the intended real account

```powershell
uv run grandmaster-fx mt5 terminal
uv run grandmaster-fx mt5 account
```

Verify account number, server, real-account mode, balance, equity, and permissions.

## 3. Profile status

```powershell
uv run grandmaster-fx live status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
```

## 4. Validate a pending request

```powershell
uv run grandmaster-fx live pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
```

Expected when a valid plan exists:

```text
placed = false
validated = true
reason = dry_run_pending_plan_validated
```

## 5. Observe state

```powershell
uv run grandmaster-fx live pending-list
uv run grandmaster-fx live pending-reconcile
Get-Content .\data\execution\live\journal.jsonl -Tail 50
```

## 6. Stop

```powershell
uv run grandmaster-fx live stop
```

Do not change `dry_run` as a troubleshooting shortcut.

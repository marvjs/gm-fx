# Grandmaster FX Operations Runbook

This runbook is the operational sequence. Detailed explanations are in `docs/`.

## Start-of-session checklist

```powershell
uv sync --locked
uv run grandmaster-fx --version
uv run grandmaster-fx mt5 terminal
uv run grandmaster-fx mt5 account
```

Confirm the intended account and server before profile commands.

## Research session

```powershell
uv run grandmaster-fx predictions inspect USDJPY --strategy momentum_continuation --timeframe M5
uv run grandmaster-fx backtest run USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --no-predictions
uv run grandmaster-fx backtest run USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
uv run grandmaster-fx pending backtest USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
uv run grandmaster-fx research validate USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
uv run grandmaster-fx research robustness USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
```

## Demo session

1. Set `mode = "demo"` and `allow_live_account = false`.
2. Connect MT5 to demo.
3. Run status.
4. Run one cycle before continuous operation.
5. Reconcile pending state.
6. Start dashboard.

```powershell
uv run grandmaster-fx demo status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo cycle --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx demo pending-reconcile
uv run grandmaster-fx demo dashboard --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
```

Stop:

```powershell
uv run grandmaster-fx demo stop
```

## Live dry-run session

1. Set `mode = "live"` and `allow_live_account = true`.
2. Keep live `dry_run = true`.
3. Connect the intended real account.
4. Run status.
5. Validate one pending request.
6. List and reconcile.
7. Preserve journal output.

```powershell
uv run grandmaster-fx live status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
uv run grandmaster-fx live pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
uv run grandmaster-fx live pending-list
uv run grandmaster-fx live pending-reconcile
Get-Content .\data\execution\live\journal.jsonl -Tail 50
```

## Incident procedure

1. Stop the affected profile.
2. Do not delete state.
3. Record account, server, active orders, positions, and tickets.
4. Back up journal and registry.
5. Run pending reconciliation.
6. Compare broker and local ownership.
7. Resolve `externally_modified`, `missing`, or `unknown` deliberately.
8. Restart only after state agrees.

## End-of-session checklist

```powershell
uv run grandmaster-fx demo pending-reconcile
uv run grandmaster-fx live pending-reconcile
```

Use only the command matching the active profile. Save important reports and journal evidence.

## Release gate

```powershell
uv run ruff format .
uv run ruff check --fix .
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=grandmaster_fx --cov-report=term-missing
```

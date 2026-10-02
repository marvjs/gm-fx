# Demo Quick Start

## 1. Configure demo mode

```toml
# configs/app.toml
[execution]
mode = "demo"
allow_live_account = false
```

Review `configs/demo_execution.toml`, especially `dry_run`, magic, comment, and risk settings. Connect MT5 to a demo account.

## 2. Preflight

```powershell
uv run grandmaster-fx mt5 doctor
uv run grandmaster-fx mt5 account
uv run grandmaster-fx demo status --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
```

## 3. Research first

```powershell
uv run grandmaster-fx pending backtest USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
```

## 4. Place one demo pending candidate

```powershell
uv run grandmaster-fx demo pending-place USDJPY --strategy momentum_continuation --timeframe M5 --direction BUY --predictions
```

`primary_signal_hold` is normal and means no order was created.

## 5. Monitor

```powershell
uv run grandmaster-fx demo pending-list
uv run grandmaster-fx demo pending-reconcile
uv run grandmaster-fx demo dashboard --strategy momentum_continuation --timeframe M5 --symbol USDJPY --direction BUY
```

## 6. Cancel an owned order

```powershell
uv run grandmaster-fx demo pending-cancel 12345678
```

## 7. Stop

```powershell
uv run grandmaster-fx demo stop
```

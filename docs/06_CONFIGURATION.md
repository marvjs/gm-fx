# Configuration Reference

All configuration is TOML and strictly validated. Unknown fields, missing required fields, invalid enums, and out-of-range values fail closed.

## Editing workflow

1. Stop the related worker.
2. Commit or back up the current configuration.
3. Change one conceptual setting.
4. Run `show-config` or the relevant config command.
5. Run unit tests and research comparisons.
6. Run paper or demo validation before live use.

## `configs/app.toml`

Controls global application and execution mode.

Demo profile:

```toml
[execution]
mode = "demo"
allow_live_account = false
```

Live profile:

```toml
[execution]
mode = "live"
allow_live_account = true
```

`mode` controls which execution command group may run. `allow_live_account` is an explicit additional authorization gate.

## `configs/demo_execution.toml`

Typical sections configure:

```toml
[execution]
enabled = true
dry_run = false
magic = 771100
comment = "grandmaster-fx-demo"
deviation_points = 10

[worker]
poll_interval_seconds = 5
maximum_cycles = 0
```

- `enabled`: profile-level execution feature switch.
- `dry_run`: validate requests without broker submission when true.
- `magic`: ownership identifier. Do not share it with live.
- `comment`: broker-visible ownership label.
- `deviation_points`: allowed price deviation for market execution.
- worker timing values control polling, not candle creation.

## `configs/live_execution.toml`

Keep live dry-run enabled during validation:

```toml
[execution]
enabled = true
dry_run = true
magic = 771101
comment = "grandmaster-fx-live"
deviation_points = 10
```

Never reuse demo magic, comments, journals, consumed state, or stop files.

## `configs/risk.toml`

Controls position sizing and circuit breakers. Typical concepts include:

```toml
[risk]
risk_per_trade_percent = 1.0
maximum_positions = 1
maximum_daily_loss_percent = 3.0
maximum_floating_loss_percent = 2.0
```

Interpretation:

- Risk per trade is based on entry-to-stop distance, not a fixed lot.
- Maximum positions limits concurrent exposure.
- Daily-loss and floating-loss thresholds stop new exposure or trigger configured protective behavior.

Use conservative values until broker and strategy behavior are proven.

## `configs/symbols.toml`

Controls the allowed currency universe, preferred pairs, and symbol resolution behavior. Use it to restrict the system to intended instruments rather than every broker symbol.

Validate changes:

```powershell
uv run grandmaster-fx symbols validate USDJPY EURUSD GBPUSD
```

## `configs/backtest.toml`

Typical sections:

```toml
[backtest]
initial_balance = 10000.0
risk_per_trade_percent = 1.0
commission_per_lot_round_turn = 0.0
slippage_points = 0.0
maximum_holding_bars = 10
minimum_history_bars = 100
conservative_same_bar_exit = true

[quality]
maximum_gap_multiple = 3
reject_history_gaps = false
maximum_data_age_hours = 24
```

- Increase costs to test fragility.
- `conservative_same_bar_exit` avoids optimistic target/stop ordering assumptions.
- Data-quality settings control gaps and stale data handling.

## `configs/research.toml`

Controls holdout fractions, walk-forward windows, cost scenarios, and robustness settings. Do not optimize repeatedly on the same final holdout.

## `configs/experiments.toml`

Defines strategy manifests, enabled candidates, comparison settings, and research eligibility. An execution eligibility field in research configuration is not the same as authorizing the demo or live CLI profile.

## `configs/predictions.toml`

Controls:

- Regime classifier thresholds
- Strategy eligibility per regime
- Higher-timeframe confirmation timeframe
- Direction agreement requirements
- Momentum thresholds

Example conceptual structure:

```toml
[confirmation]
timeframe = "M15"
require_direction_match = true
minimum_momentum = 0.0

[regimes.trending]
strategies = ["momentum_continuation", "donchian_breakout"]

[regimes.ranging]
strategies = ["channel_mean_reversion", "extreme_mean_reversion"]
```

Use the exact keys already present in your file. Do not invent keys outside the validated schema.

## `configs/pending_orders.toml`

Conceptual example:

```toml
[pending]
enabled = true
trigger_offset_atr = 0.10
maximum_wait_bars = 3
replacement_policy = "retain_existing"
allow_market = false
allow_stop = true
allow_limit = false
```

- `trigger_offset_atr`: how far beyond the reference range the trigger is placed.
- `maximum_wait_bars`: completed bars before expiration.
- `replacement_policy`: behavior when equivalent active state exists.
- order-type switches control which plan types the planner may produce.

## `configs/paper_worker.toml`

Controls the broker-free continuous worker, including initial balance, symbol/timeframe defaults, poll interval, and paper-specific behavior.

## `configs/strategies/*.toml`

Each strategy file defines its own periods, thresholds, stop/target logic, volatility constraints, and session settings. Use the strategy identifier in CLI commands and edit the matching file.

## Validation commands

```powershell
uv run grandmaster-fx show-config
uv run grandmaster-fx predictions config
uv run grandmaster-fx doctor
uv run grandmaster-fx demo status ...
uv run grandmaster-fx live status ...
```

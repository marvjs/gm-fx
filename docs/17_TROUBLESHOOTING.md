# Troubleshooting

## `primary_signal_hold`

The selected strategy found no BUY or SELL setup on the last completed candle. Wait for another completed candle or research another strategy. Do not force an order.

## `strategy_not_allowed`

The strategy is not eligible for the classified regime. Inspect `configs/predictions.toml` and compare with `--no-predictions` for research only.

## `direction_mismatch`

Higher-timeframe confirmation points against the raw signal.

## `momentum_too_weak`

Direction may agree, but the higher-timeframe momentum threshold is not met.

## `existing_order_retained`

An equivalent profile-owned pending order already exists. List and inspect it.

## `existing_position_conflict`

A profile-owned position already conflicts with the candidate.

## `broker_confirmation_missing`

Do not retry immediately. List and reconcile active orders, positions, and history.

## `externally_modified`

The broker order differs from the stored plan. Compare price, stop, target, volume, type, symbol, and direction.

## `missing`

No match was found in active orders, positions, or the history window. Check account/server, ticket, magic, and MT5 history.

## Duplicate cycle

Repeated polling inside one candle can return duplicate state. The system uses completed candles.

## Wrong profile mode

Demo commands require `mode = "demo"`. Live commands require `mode = "live"` and explicit authorization.

## Wrong account mode

Demo requires a demo account. Live requires a real account.

## `ty` command not found

The project quality gate uses mypy. A VS Code extension may provide separate `ty` diagnostics even if the CLI package is not installed.

## Coverage below 90%

Do not lower the threshold. Add focused tests for new branches.

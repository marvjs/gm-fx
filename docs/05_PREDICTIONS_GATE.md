# Prediction Gate

## What `--predictions` means

The option does not call an external AI service and does not promise the next price. It enables a deterministic acceptance layer after the chosen strategy produces BUY, SELL, or HOLD.

With `--predictions`:

```text
Raw strategy decision
→ Market-regime classification
→ Is this strategy eligible in that regime?
→ Is higher-timeframe direction aligned?
→ Is higher-timeframe momentum strong enough?
→ Final accepted or rejected decision
```

With `--no-predictions`:

```text
Raw strategy decision
→ Direction filter
→ Continue without regime and MTF confirmation
```

## Why compare both

Predictions may improve selectivity but reduce trade count. A higher win rate with only a few trades may be less reliable than a slightly lower win rate with stable evidence. Always compare:

```text
Raw strategy
Prediction-gated strategy
Pending raw strategy
Pending prediction-gated strategy
```

## Typical rejection reasons

- `strategy_not_allowed`: the selected strategy is not eligible in the classified regime.
- `direction_mismatch`: the higher timeframe points against the raw signal.
- `momentum_too_weak`: direction may agree but confirmation momentum is below threshold.
- `regime_mismatch`: the setup does not fit the required regime.
- `primary_signal_hold`: the strategy itself produced HOLD before prediction checks.

## Commands

```powershell
uv run grandmaster-fx predictions config
uv run grandmaster-fx predictions inspect USDJPY --strategy momentum_continuation --timeframe M5
```

Research comparison:

```powershell
uv run grandmaster-fx backtest run USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
uv run grandmaster-fx backtest run USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --no-predictions
```

## Configuration

`configs/predictions.toml` controls regime thresholds, eligible strategies by regime, confirmation timeframe, directional agreement, and momentum thresholds. See `06_CONFIGURATION.md` before editing it.

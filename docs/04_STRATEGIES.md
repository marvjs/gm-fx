# Strategy Guide

## Important: there is no single best strategy

“Best” must be defined by evidence. A strategy is preferable only for a specific symbol, timeframe, direction, date range, cost model, and regime. Select strategies by holdout and walk-forward results, not by name or one profitable run.

## Strategy catalogue

### `baseline_scalper`

A general baseline strategy combining short-term market information and protective filters. Use it as a reference model and sanity check.

Best use: baseline comparisons and liquid intraday conditions.

Main risk: frequent signals can be sensitive to spread, slippage, and session quality.

Example:

```powershell
uv run grandmaster-fx backtest run USDJPY --strategy baseline_scalper --timeframe M5 --count 20000 --direction ALL --no-predictions
```

### `channel_mean_reversion`

Looks for price displacement relative to a recent channel and expects movement back toward the center.

Best use: ranging or low-trend markets.

Main risk: persistent trends can continue moving against a mean-reversion entry.

### `donchian_breakout`

Trades breaks beyond a recent Donchian high or low.

Best use: sustained trend and breakout regimes.

Main risk: false breakouts and whipsaws in ranges.

### `extreme_mean_reversion`

Waits for a more extreme displacement before seeking reversion.

Best use: overextended range conditions where ordinary mean reversion is too permissive.

Main risk: an “extreme” move can be the start of a genuine trend.

### `fibonacci_pullback`

Looks for a retracement inside a preceding directional move and attempts to join the original direction.

Best use: orderly trends with pullbacks.

Main risk: the pullback may become a full reversal.

### `momentum_continuation`

Looks for an established directional move with sufficient momentum and attempts continuation.

Best use: directional, liquid sessions where higher-timeframe confirmation agrees.

Main risk: late entry after momentum exhaustion.

This was the primary candidate exercised during the completed pending-order work, but that does not make it universally superior.

### `session_range_breakout`

Builds a range from a configured session window and trades a break from that range.

Best use: instruments that often expand after a known consolidation session.

Main risk: session boundaries and broker/server time interpretation must match the configuration.

### `volatility_expansion`

Looks for volatility increasing beyond a quieter baseline and enters in the expansion direction.

Best use: transitions from compression to active movement.

Main risk: one-bar shocks and news spikes can look like valid expansion.

### `volatility_expansion_window`

A window-aware volatility expansion strategy that adds contextual timing or rolling-window constraints.

Best use: controlled expansion setups where a generic volatility trigger is too broad.

Main risk: more parameters can increase overfitting risk.

## How to choose a strategy

Use this procedure:

1. Run every plausible strategy on the same symbol, timeframe, direction, count, and cost model.
2. Compare raw signals with `--no-predictions`.
3. Compare the same strategy with `--predictions`.
4. Reject candidates with too few trades for meaningful inference.
5. Review drawdown, profit factor, expectancy, consecutive losses, and stability, not return alone.
6. Run chronological holdout validation.
7. Run robustness and cost sensitivity.
8. Repeat on another time range.
9. Test paper lifecycle.
10. Test demo execution and broker behavior.

## Suggested regime mapping

```text
Strong trend or breakout:
  donchian_breakout
  momentum_continuation
  volatility_expansion
  volatility_expansion_window

Orderly trend with retracement:
  fibonacci_pullback

Range or reversion:
  channel_mean_reversion
  extreme_mean_reversion

Session-specific expansion:
  session_range_breakout

Reference behavior:
  baseline_scalper
```

This mapping is a research starting point, not an execution guarantee. The actual prediction configuration controls which strategies are eligible in each classified regime.

## Strategy configuration

Each strategy has a TOML file under:

```text
configs/strategies/
```

Typical settings control lookback periods, thresholds, volatility limits, stop and target multipliers, session windows, and minimum setup quality. Change one conceptual variable at a time, commit the change, and rerun holdout and robustness tests.

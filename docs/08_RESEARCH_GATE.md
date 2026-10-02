# Backtest and Research Gate

## Standard backtest

```powershell
uv run grandmaster-fx backtest run USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
```

## Metrics

- Trades: sample size
- Final balance and return: overall outcome
- Maximum drawdown: peak-to-trough decline
- Win rate: winning trades divided by all closed trades
- Profit factor: gross profit divided by gross loss
- Expectancy: average net result per trade
- Maximum consecutive losses: operational and psychological stress indicator

Do not use win rate alone. A strategy can win often and still lose money.

## Holdout validation

```powershell
uv run grandmaster-fx research validate USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
```

The final segment must remain untouched during strategy development.

## Robustness

```powershell
uv run grandmaster-fx research robustness USDJPY --strategy momentum_continuation --timeframe M5 --count 20000 --direction BUY --predictions
```

Review walk-forward consistency, cost sensitivity, direction asymmetry, and holding-period sensitivity.

## Acceptance process

A candidate should advance only if:

1. Trade count is sufficient for its frequency.
2. Drawdown is acceptable.
3. Profit factor and expectancy remain positive after realistic costs.
4. Holdout performance does not collapse.
5. Walk-forward segments are not dominated by one lucky period.
6. The prediction-gated version improves the desired objective without destroying sample size.
7. Paper and demo behavior matches the simulation assumptions.

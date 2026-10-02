# Market Data Gate

## Purpose

Ensure that strategies never operate on malformed, unordered, duplicated, stale, or incomplete candles.

## Commands

```powershell
uv run grandmaster-fx data tick USDJPY
uv run grandmaster-fx data bars USDJPY --timeframe M5 --count 500
uv run grandmaster-fx data export USDJPY --timeframe M5 --count 10000
```

## Completed candles

The execution and research pipeline evaluates completed candles. Polling every few seconds does not create a new M5 opportunity. Multiple cycles inside one candle can legitimately report duplicate state.

## Symbol resolution

A user-facing pair such as `USDJPY` may resolve to `USDJPYm`, `USDJPY.a`, or another broker-specific form. Always inspect the resolved symbol and trading properties.

## Failure conditions

- Too few bars
- Duplicate timestamps
- Unsorted or invalid OHLC data
- Excessive gaps when rejection is enabled
- Stale data
- Unsupported symbol
- Terminal retrieval failure

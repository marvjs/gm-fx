# System Concepts and Gates

Grandmaster FX is deliberately gated. Each gate has one responsibility and may reject the candidate.

## 1. Configuration gate

Loads strictly validated TOML configuration. Unknown keys and invalid values fail before trading logic runs.

## 2. MT5 gate

Validates terminal initialization, API access, account mode, trading permission, expert permission, and symbol availability.

## 3. Market-data gate

Retrieves completed candles, sorts them chronologically, rejects malformed or duplicate data, and applies configured gap or age rules.

## 4. Strategy gate

A selected strategy returns BUY, SELL, or HOLD plus entry, stop, target, score, and reasons. HOLD stops the pipeline.

## 5. Direction gate

`--direction ALL` accepts BUY and SELL. `BUY` rejects SELL. `SELL` rejects BUY. Use direction filtering to test asymmetric performance rather than assuming both sides behave equally.

## 6. Prediction gate

When `--predictions` is enabled, the raw signal must also pass regime eligibility and higher-timeframe confirmation. When disabled, the raw strategy decision proceeds without those prediction filters.

## 7. Pending gate

When using pending commands, the accepted strategy decision is converted into a future trigger plan. The current configuration may permit stop orders, limit orders, or both.

## 8. Risk gate

Calculates volume from balance, risk percentage, entry-to-stop distance, tick value, tick size, minimum volume, maximum volume, and volume step. It also applies operational circuit breakers.

## 9. Execution-profile gate

- Paper uses local state.
- Demo requires application mode `demo` and an MT5 demo account.
- Live requires application mode `live`, explicit live authorization, and an MT5 real account.

## 10. Broker gate

Builds and checks the exact request. A pending request calls `order_check` before submission. Dry-run stops after validation.

## 11. Confirmation gate

A returned ticket is not enough. Live pending placement queries broker state and verifies the ticket and requested fields.

## 12. Observability gate

Journals the lifecycle, persists ownership, lists active orders, and reconciles orders against positions and history.

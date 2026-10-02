# Risk Gate

## Position sizing

Volume is calculated from:

```text
Account balance or equity
Risk percentage
Entry-to-stop distance
Tick size
Tick value
Contract properties
Broker minimum volume
Broker maximum volume
Broker volume step
```

A wider stop produces a smaller volume for the same cash risk.

## Operational controls

- Maximum open positions
- Daily-loss circuit breaker
- Floating-loss circuit breaker
- Symbol and profile ownership checks
- Duplicate signal and pending-order checks
- Stop file
- Dry-run

## Practical guidance

- Start with the smallest reasonable risk percentage.
- Test cost sensitivity.
- Count active pending exposure when reviewing total risk.
- Never increase risk to compensate for recent losses.
- Confirm normalized volume in the broker request.

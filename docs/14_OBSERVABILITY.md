# Observability and Reconciliation

## Journals

```text
data/execution/demo/journal.jsonl
data/execution/live/journal.jsonl
```

Each line is a JSON event with UTC timestamp and lifecycle payload.

## Live registry

```text
data/execution/live/pending_orders.json
```

It maps deterministic plan identity to broker ticket and expected request fields.

## Reconciliation sources

```text
Active broker pending orders
Open broker positions
Recent order history
Recent deal history
Local live registry
```

## State interpretation

- `active`: matching pending order exists.
- `triggered`: matching position exists.
- `filled`: matching deal exists.
- `canceled`: broker history reports cancellation.
- `expired`: broker history reports expiration.
- `rejected`: broker history reports rejection.
- `externally_modified`: active broker fields differ from the stored plan.
- `missing`: no active, position, deal, or history match was found.
- `unknown`: history exists but cannot be classified safely.

## Incident rule

Do not manually delete ownership data first. Back up the registry and journal, inspect MT5, run reconciliation, and only then repair state through an explicit procedure.

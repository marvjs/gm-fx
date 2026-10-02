# Testing and Release Gate

## Format and lint

```powershell
uv run ruff format .
uv run ruff check --fix .
uv run ruff format --check .
uv run ruff check .
```

## Type check

```powershell
uv run mypy
```

## Full tests and coverage

```powershell
uv run pytest `
  --cov=grandmaster_fx `
  --cov-report=term-missing
```

Expected baseline:

```text
294 passed
Coverage at or above 90%
```

## Focused pending regression

```powershell
uv run pytest `
  tests/unit/test_pending_historical.py `
  tests/unit/test_pending_complete_coverage.py `
  tests/unit/test_live_pending_observability.py `
  tests/unit/test_live_pending_additional_coverage.py `
  -vv
```

## Release checklist

1. Review the Git diff.
2. Confirm version sources agree.
3. Confirm lockfile is current.
4. Run the full quality gate.
5. Confirm demo and live magic numbers remain isolated.
6. Confirm live `dry_run` value is intentional.
7. Confirm no `.env`, credentials, live registry, journal, or broker export is included.
8. Update CHANGELOG and documentation.
9. Create a clean checkpoint.

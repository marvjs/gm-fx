# Changelog

## 1.7.0 - 2026-10-06

### Added
- Demo multi-symbol execution worker to continuously poll and trade via the `DemoExecutionManager`.
- Real-time `demo run`, `demo cycle`, `demo status`, and `demo stop` Typer CLI commands.
- Centralized `StrategyRegistry` injection for safe execution reuse alongside `experiments`.

## 1.6.4 - 2026-09-29

### Fixed

- Added focused coverage for execution validation, journal persistence, configuration failures, paper accounting, missing state, and bounded worker runs.
- Restored the enforced 90 percent coverage threshold without exclusions.


## 1.6.3 - 2026-09-29

### Fixed

- Completed strict Ruff exception, annotation, boolean-argument, and print compliance.
- Added concrete paper-worker CLI typing and Timeframe protocol annotations.


## 1.6.2 - 2026-09-29

### Fixed

- Increased the synthetic paper trend strength so its combined candidate score clears the configured 0.60 minimum.
- Kept the production scoring threshold and worker logic unchanged.


## 1.6.1 - 2026-09-29

### Fixed

- Strengthened the synthetic paper-worker trend fixture so it clears the configured momentum threshold.
- Preserved valid OHLC relationships while testing simulated opening and profit closure.


## 1.6.0 - 2026-09-29

### Added

- Continuous broker-free paper worker with multi-symbol scanning and ranked simulated entries.
- Persistent paper positions, balance, equity, realized profit, cooldowns, and atomic restart recovery.
- Small-profit, high-water retracement, stop-loss, and price-target exits using live read-only MT5 prices.
- Paper status, cycle, run, and stop CLI commands.


## 1.5.1 - 2026-09-29

### Fixed

- Added the missing pathlib.Path import to the demo execution settings test.


## 1.5.0 - 2026-09-29

### Added

- Demo-only multi-symbol execution manager with ranked candidates and one-position-per-symbol enforcement.
- Small-profit and high-water profit-retracement exits.
- Daily and floating-loss circuit breakers, cooldowns, dry-run default, and append-only journal.
- Demo-account guards on every position and order operation.


## 1.4.7 - 2026-09-29

### Fixed

- Corrected candidate decision fixtures so their final candle lands at the requested UTC hour.
- Kept session-range BUY, SELL, spread, and volatility tests inside the configured entry window.


## 1.4.6 - 2026-09-29

### Fixed

- Added direct BUY, SELL, HOLD, quality-rejection, and loader-failure coverage for every consolidated candidate.
- Restored the enforced project coverage threshold without excluding production strategy modules.


## 1.4.5 - 2026-09-29

### Fixed

- Replaced the candidate loader using formatting-independent source boundaries.
- Moved annotation-only imports behind TYPE_CHECKING.
- Removed legacy TypeVar and redundant cast usage.


## 1.4.3 - 2026-09-29

### Fixed

- Recovered mixed 1.4.x patch states.
- Deferred candidate protocol annotations to prevent CandidateContext import failures.
- Completed strict Ruff and mypy annotations idempotently.


## 1.4.2 - 2026-09-29

### Fixed

- Added strict generic and protocol typing to the consolidated candidate pack.
- Documented intentional orchestration and decision-branch complexity for Ruff.
- Added the missing expansion-window test helper return annotation.


## 1.4.1 - 2026-09-29

### Fixed

- Removed the unsupported indicators.roc package import.
- Added a local vectorized percentage rate-of-change helper for momentum research.


## 1.4.0 - 2026-09-29

### Added

- Consolidated session-range breakout, Fibonacci pullback, channel mean-reversion, and momentum-continuation candidates.
- Indexed contexts, fixed ATR protection, and automatic experiment registration for every candidate.
- No loss-based sizing, averaging down, grid recovery, or martingale progression.


## 1.3.2 - 2026-09-29

### Fixed

- Corrected the expansion-window BUY fixture so the actual latest Bar closes above the prior range.
- Kept the production strategy dependent on market Bar data rather than synthetic context close values.


## 1.3.1 - 2026-09-29

### Fixed

- Corrected the expansion-window BUY fixture to use ATR values inside the configured volatility range.
- Preserved a genuine first expansion-threshold crossing in the actionable-signal test.


## 1.3.0 - 2026-09-29

### Added

- Independent three-candle expansion-window hypothesis after recent compression.
- Six-candle compression-event lookback with first-crossing duplicate suppression.
- Indexed event-age context and automatic quick/full eligibility integration.


## 1.2.2 - 2026-09-29

### Fixed

- Replaced alphabetic diagnostic subtraction with a true stage-ordered filter funnel.
- Added monotonic funnel invariants and survival percentages.
- Added regression evidence for the observed EURUSD volatility-expansion profile.


## 1.2.1 - 2026-09-29

### Fixed

- Updated the actual Block 10.1 experiment fixtures for filter-funnel diagnostics.
- Added stage timing evidence to the exported outcome fixture.


## 1.2.0 - 2026-09-29

### Added

- Precomputed indexed volatility-expansion indicators for linear historical evaluation.
- Decision-reason filter funnels and per-stage experiment timing.
- Indexed strategy protocol with compatibility fallback for existing strategies.


## 1.1.5 - 2026-09-29

### Fixed

- Replaced the corrupted shared-strategy helper test with a complete syntax-checked version.
- Added explicit optional-price narrowing before ordering assertions.


## 1.1.4 - 2026-09-29

### Fixed

- Declared the Typer Boolean option with positional parameter declarations supported by the installed API.
- Preserved the ResearchStrategy protocol parameter name in the runner test while explicitly consuming the unused value.
- Restored CLI importability and strict ty compatibility.


## 1.1.3 - 2026-09-29

### Fixed

- Replaced oversized protection helper arguments with an immutable proposal object.
- Moved Typer option construction to module-level singletons and isolated empty-selection validation.
- Added strict cache-test typing and deterministic passing activity diagnostics to experiment tests.


## 1.1.2 - 2026-09-29

### Fixed

- Applied Block 10.1 test corrections independently of Ruff formatting.
- Updated the actual diagnostics test method instead of searching the runner test.
- Rebuilt the experiment outcome fixture with explicit mode, timing, diagnostics, and optional evidence fields.


## 1.1.0 - 2026-09-29

### Added

- Quick and full experiment modes with quick as the development default.
- Per-strategy selection, progress, elapsed timing, and decision diagnostics.
- Exact-request local candle caching under data/cache/market.
- Low signal-frequency and low trade-count fail-closed eligibility diagnostics.


## 1.0.2 - 2026-09-29

### Fixed

- Patched frozen strategy methods at the class level in Block 10 decision-path tests.
- Preserved immutable strategy instances while retaining deterministic branch coverage.


## 1.0.1 - 2026-09-29

### Fixed

- Added public decision-path coverage for both Block 10 hypotheses.
- Added direct coverage for shared HOLD and ATR-protection helpers.
- Restored the enforced coverage threshold without excluding strategy modules.


## 1.0.0 - 2026-09-29

### Added

- Volatility expansion breakout research hypothesis.
- Extreme displacement mean-reversion research hypothesis.
- Shared immutable ATR protection and HOLD-decision helpers.
- Automatic inclusion of both hypotheses in measured Block 9.1 eligibility experiments.


## 0.9.6 - 2026-09-29

### Added

- True chronological holdout backtests for every strategy experiment.
- Measured walk-forward stability and cost-sensitivity eligibility evidence.
- Full-sample, holdout, fold, sensitivity, and threshold details in comparison exports.


## 0.9.5 - 2026-09-29

### Fixed

- Corrected the experiment-runner test fixture to satisfy the validated minimum history requirement.


## 0.9.4 - 2026-09-29

### Fixed

- Added direct decision-path coverage for the Donchian breakout hypothesis.
- Added experiment orchestration, export, duplicate-manifest, and unregistered-strategy tests.
- Restored the enforced project coverage threshold without exclusions.


## 0.9.3 - 2026-09-29

### Fixed

- Replaced oversized experiment calls with an immutable request model.
- Made eligibility booleans keyword-only.
- Refactored Donchian evaluation into focused validation, filtering, and signal helpers.
- Updated backtest tests to use the ResearchStrategy protocol adapter.
- Replaced robustness magic values with named constants.


## 0.9.2 - 2026-09-29

### Fixed

- Typed baseline adapter configuration paths as pathlib.Path instead of object.
- Removed the unnecessary and unsafe Path(object) conversion.


## 0.9.1 - 2026-09-29

### Fixed

- Dispatched backtests through the ResearchStrategy protocol instead of the concrete baseline evaluator.
- Updated deterministic engine tests to patch the protocol dispatch seam.


## 0.9.0 - 2026-09-29

### Added

- Research strategy protocol, registry, and manifest-driven factories.
- Reproducible experiment identifiers and machine-readable comparisons.
- Donchian breakout research hypothesis alongside the rejected baseline.
- Hard eligibility gates with execution globally disabled.


## 0.8.5 - 2026-09-28

### Fixed

- Applied strict robustness typing independently of Ruff import formatting.
- Used distinct typed loop variables for sensitivity and ablation rendering.


## 0.8.3 - 2026-09-28

### Added

- Anchored walk-forward simulation with fold-level stability statistics.
- Commission and slippage sensitivity simulations.
- BUY, SELL, short-hold, and long-hold diagnostic ablations.
- Machine-readable robustness reports and terminal summaries.


## 0.8.2 - 2026-09-28

### Fixed

- Stored the actual simulated entry timestamp in OpenTrade.
- Preserved entry_time separately from exit_time in every trade-ledger row.
- Added timeline invariants and regression tests for multi-bar and same-bar exits.


## 0.8.1 - 2026-09-28

### Fixed

- Replaced research split and losing-streak magic values with named constants.
- Corrected the export test to validate serialized verdict fidelity rather than force a passing economic result.


## 0.8.0 - 2026-09-28

### Added

- Chronological holdout validation and anchored walk-forward window generation.
- Trade attribution by direction, exit reason, hour, and weekday.
- Gross-versus-cost analysis and machine-readable research exports.
- Explicit validation thresholds, warnings, and pass/fail verdicts.


## 0.7.6 - 2026-09-28

### Fixed

- Replaced every partial historical-gap implementation with one known-good module.
- Made the recovery patch transactional and idempotent across versions 0.7.2 through 0.7.5.
- Added tolerant-mode and strict-mode regression tests.


## 0.7.2 - 2026-09-28

### Fixed

- Added direct backtest engine coverage for sizing, exits, costs, no-signal runs, trade closure, and end-of-data handling.
- Added complete historical quality and backtest configuration error-path tests.


## 0.7.1 - 2026-09-28

### Fixed

- Replaced oversized backtest function signatures with typed request and close-context models.
- Made engine exceptions compliant with strict Ruff rules.
- Replaced successive-pair zip logic with itertools.pairwise.
- Corrected the known-value profit-factor assertion from 2.0 to 100/75.


## 0.7.0 - 2026-09-28

### Added

- Chronological no-lookahead backtesting engine.
- Spread-aware entries, slippage, commission, ATR exits, and time stops.
- Trade ledger, equity curve, drawdown, profit factor, expectancy, and streak metrics.
- Historical gap and age diagnostics.


## 0.6.1 - 2026-09-28

### Fixed

- Decomposed baseline evaluation into focused preflight, indicator, filter, setup, protection, and decision helpers.
- Added coverage for disabled, session, volatility, and invalid-input paths.


## 0.6.0 - 2026-09-28

### Added

- Explainable BUY, SELL, and HOLD strategy decisions.
- EMA trend, pullback, momentum, RSI, ATR, spread, and UTC session filters.
- ATR-derived non-executable stop and target proposals.
- Versioned strategy configuration and Rich inspection output.


## 0.5.3 - 2026-09-28

### Fixed

- Typed parametrized invalid indicator inputs as NumPy ArrayLike values.
- Removed the editor and strict type-checker mismatch at the sma test call.


## 0.5.2 - 2026-09-28

### Fixed

- Added an explicit FloatArray annotation for NumPy true-range reduction output.
- Made the SMA property test tolerant of representational floating-point error.


## 0.5.1 - 2026-09-28

### Fixed

- Made indicator validation exceptions compliant with Ruff EM101 and TRY003.
- Corrected pytest parametrization and narrowed the expected validation error.


## 0.5.0 - 2026-09-28

### Added

- Pure NumPy SMA, EMA, RSI, true range, ATR, rate-of-change, volatility, rolling-extreme, and candle metrics.
- Rich indicator inspection from completed MT5 candles.
- Known-value, edge-case, and property-based indicator tests.


## 0.4.2 - 2026-09-28

### Fixed

- Converted NumPy structured MT5 candle rows by dtype field name instead of calling dict(row).
- Added regression coverage for real copy_rates_from_pos row behavior.


## 0.4.1 - 2026-09-28

### Fixed

- Added missing MT5 market-data gateway and service orchestration tests.
- Restored the enforced coverage gate above 90 percent.


## 0.3.0 - 2026-09-28

### Added

- Currency-only symbol discovery and broker suffix resolution.
- Rich symbol listing, inspection, and validation commands.
- Broker metadata snapshots, volume normalization, spread conversion, and Market Watch selection.
- Versioned currency allowlist and symbol validation configuration.


## 0.2.1 - 2026-09-28

### Fixed

- Made the MT5 terminal-path assertion platform-neutral so the test passes with Windows path normalization.


## 0.2.0 - 2026-09-28

### Added

- Official MetaTrader 5 Windows dependency.
- Read-only MT5 terminal initialization and explicit login support.
- Environment-backed private connection settings.
- Demo-account-only safety validation.
- Sanitized terminal and account diagnostics.
- `mt5 doctor`, `mt5 terminal`, and `mt5 account` commands.
- Mocked MT5 unit tests that never contact a broker.

## 0.1.0 - 2026-09-28

- Initial project foundation.

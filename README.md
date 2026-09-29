# Grandmaster FX

Grandmaster FX is a staged, deterministic forex trading-system project for MetaTrader 5. Block 1 provides the safe and testable project foundation only. It does **not** connect to MetaTrader 5, retrieve market data, produce signals, or place trades.

## Safety status

- Live-account execution is structurally rejected.
- The default execution mode is `observe`.
- No broker connection exists in Block 1.
- No strategy or order execution exists in Block 1.
- Profit is not guaranteed. Any later strategy must pass historical and demo validation.

## Requirements

- Windows 10 or Windows 11
- PowerShell 7 or Windows PowerShell 5.1
- [uv](https://docs.astral.sh/uv/) installed and available on `PATH`
- Internet access for the initial dependency synchronization

Confirm uv is installed:

```powershell
uv --version
```

If it is not installed, use the official Windows installer command:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Close and reopen PowerShell after installation if `uv` is not immediately found.

## Extract the archive

The archive is expected at:

```text
$Home\Downloads\grandmaster-fx.zip
```

Create and enter the project directory, then extract the archive contents directly into it:

```powershell
New-Item -ItemType Directory -Force -Path "$Home\grandmaster-fx" | Out-Null
Set-Location "$Home\grandmaster-fx"
Expand-Archive -Path "$Home\Downloads\grandmaster-fx.zip" -DestinationPath . -Force
```

## Install the project

From `$Home\grandmaster-fx`:

```powershell
uv python install 3.12
uv sync --locked
```

`uv sync --locked` creates `.venv` and installs the exact versions recorded in `uv.lock`.

## Run the program

```powershell
uv run grandmaster-fx --help
uv run grandmaster-fx --version
uv run grandmaster-fx doctor
uv run grandmaster-fx show-config
```

The doctor command should show four passing checks and finish with:

```text
Foundation is healthy.
```

## Quality gates

Check formatting without changing files:

```powershell
uv run ruff format --check .
```

Lint the project:

```powershell
uv run ruff check .
```

Run strict static typing:

```powershell
uv run mypy
```

Run tests and enforce the configured 90% coverage floor:

```powershell
uv run pytest --cov=grandmaster_fx --cov-report=term-missing
```

Run everything in sequence:

```powershell
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=grandmaster_fx --cov-report=term-missing
uv run grandmaster-fx doctor
```

Apply automatic formatting and safe lint fixes during development:

```powershell
uv run ruff format .
uv run ruff check --fix .
```

## Configuration

Non-secret settings live in versioned TOML files under `configs/`.

The main application file is:

```text
configs/app.toml
```

Do not set `allow_live_account` to `true`. The configuration layer rejects it.

`.env.example` documents secret names reserved for Block 2. Do not create `.env` yet because Block 1 does not read broker credentials.

## Runtime output

- Logs: `logs/grandmaster-fx.log`
- Cached data: `data/cache/`
- Exports: `data/exports/`
- Reports: `data/reports/`

Runtime contents are ignored by Git, while placeholder files preserve the directories.

## VS Code

Open the project:

```powershell
code "$Home\grandmaster-fx"
```

Select this interpreter when prompted:

```text
$Home\grandmaster-fx\.venv\Scripts\python.exe
```

If imports remain red after `uv sync --locked`, open the command palette, run **Python: Select Interpreter**, choose the project `.venv`, and then run **Developer: Reload Window**.

## Troubleshooting

### `uv` is not recognized

Reopen PowerShell. Then verify:

```powershell
uv --version
```

### Lockfile mismatch

Do not regenerate the lockfile first. Confirm the extracted files are current, then run:

```powershell
uv sync --locked
```

### Python version mismatch in doctor

```powershell
uv python install 3.12
Remove-Item -Recurse -Force .venv
uv sync --locked
```

### Detailed tests

```powershell
uv run pytest -vv
```

### Clean local generated state

```powershell
Remove-Item -Recurse -Force .venv, .pytest_cache, .ruff_cache, .mypy_cache, htmlcov -ErrorAction SilentlyContinue
Remove-Item -Force .coverage -ErrorAction SilentlyContinue
uv sync --locked
```

## Block 1 completion criteria

Block 1 is complete when all of these succeed:

```powershell
uv sync --locked
uv run ruff format --check .
uv run ruff check .
uv run mypy
uv run pytest --cov=grandmaster_fx --cov-report=term-missing
uv run grandmaster-fx doctor
```

## Block 2: MetaTrader 5 read-only connection

Block 2 adds the official Windows-only `MetaTrader5` package and read-only terminal/account diagnostics. No order is constructed or sent. Every account snapshot is validated as `DEMO`; real and contest accounts are rejected.

### Connection option A: reuse the open MT5 terminal session

Open the intended MetaTrader 5 terminal, sign in to the demo account, then run:

```powershell
uv run grandmaster-fx mt5 doctor
uv run grandmaster-fx mt5 terminal
uv run grandmaster-fx mt5 account
```

### Connection option B: explicit private credentials

Create the ignored local secrets file:

```powershell
Copy-Item .env.example .env
notepad .env
```

Set all three credential values together:

```text
MT5_LOGIN=your_demo_login
MT5_PASSWORD=your_demo_trading_password
MT5_SERVER=your_exact_demo_server
```

When multiple MT5 installations exist, set the machine-specific path as well:

```text
MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
```

Never commit `.env`. The program does not print the password and `show-config` does not load or display MT5 secrets.

### Block 2 commands

```powershell
uv run grandmaster-fx mt5 --help
uv run grandmaster-fx mt5 doctor
uv run grandmaster-fx mt5 terminal
uv run grandmaster-fx mt5 account
```

If the terminal is logged into a real account, all MT5 commands stop with exit code 2. Switch the terminal to an Exness demo account before retrying.


## Block 3: Forex symbol discovery

```powershell
uv run grandmaster-fx symbols --help
uv run grandmaster-fx symbols list
uv run grandmaster-fx symbols inspect EURUSD
uv run grandmaster-fx symbols validate EURUSD GBPUSD USDJPY
```

The discovery layer accepts only configured currency codes, resolves broker prefixes or suffixes from MT5 base/profit currency metadata, and rejects metals, indices, stocks, energy products, and crypto assets. `inspect` can select a resolved currency symbol in Market Watch before refreshing its metadata.


## Block 5: Numerical indicators

```powershell
uv run grandmaster-fx indicators --help
uv run grandmaster-fx indicators inspect EURUSD --timeframe M1 --count 200
```

Indicators operate only on completed, validated candles. Warm-up positions are represented by `NaN`; the CLI requests enough history to report fully initialized latest values.


## Block 6: Baseline strategy

```powershell
uv run grandmaster-fx strategy --help
uv run grandmaster-fx strategy inspect EURUSD --timeframe M1 --count 200
```

The strategy produces an explainable BUY, SELL, or HOLD decision only. It cannot construct or submit an order.


## Block 7: Backtesting

```powershell
uv run grandmaster-fx backtest run EURUSD --timeframe M1 --count 5000
```

Historical simulation only. Results do not guarantee future performance.


## Block 8: Strategy research and validation

```powershell
uv run grandmaster-fx research validate EURUSD --timeframe M5 --count 10000
```

The command evaluates only the chronological holdout partition and exports a trade ledger, diagnostic summary, and validation verdict. It does not submit orders.


## Block 8.1: Robustness and ablation research

```powershell
uv run grandmaster-fx research robustness EURUSD --timeframe M5 --count 10000
```

The command runs anchored out-of-sample folds, cost sensitivity, and diagnostic ablations. It remains research-only.


## Block 9: Strategy experiment framework

```powershell
uv run grandmaster-fx experiments compare EURUSD --timeframe M5 --count 10000
```

Experiments remain research-only. The global execution gate is disabled in `configs/experiments.toml`.


### Block 9.1 measured eligibility

Strategy comparisons now distinguish full-sample performance from chronological holdout performance and use measured walk-forward and cost-sensitivity evidence for every eligibility reason.


## Block 10: Research hypothesis expansion

The experiment registry now compares four fixed-parameter hypotheses: baseline scalper, Donchian breakout, volatility expansion, and extreme mean reversion. Every hypothesis automatically inherits full-sample, chronological holdout, walk-forward, cost-sensitivity, and global execution-gate evaluation.


## Block 10.1: Faster research diagnostics

Use `--strategy` to run one hypothesis and `--mode quick` for full-sample plus holdout development runs. Use `--mode full` only for final candidates because it also runs walk-forward and cost sensitivity.

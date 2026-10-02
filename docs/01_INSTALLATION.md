# Installation and Environment

## Requirements

- Windows for MetaTrader 5 integration
- MetaTrader 5 desktop terminal
- `uv`
- Python 3.12

## Install

```powershell
Set-Location "C:\path\to\grandmaster-fx"
uv python install 3.12
uv sync --locked
```

Verify:

```powershell
uv run python --version
uv run grandmaster-fx --version
uv run grandmaster-fx --help
```

## MetaTrader 5 session

The application can reuse the account already signed in to the open terminal. If explicit credentials are needed, create an untracked `.env`:

```dotenv
MT5_LOGIN=12345678
MT5_PASSWORD=replace-me
MT5_SERVER=Broker-Server
MT5_TERMINAL_PATH=C:\Program Files\MetaTrader 5\terminal64.exe
MT5_TIMEOUT_MS=60000
```

`MT5_LOGIN`, `MT5_PASSWORD`, and `MT5_SERVER` must be supplied together. Never commit `.env`.

## Connection checks

```powershell
uv run grandmaster-fx mt5 doctor
uv run grandmaster-fx mt5 terminal
uv run grandmaster-fx mt5 account
```

Check the account mode before every demo or live session. Demo commands require a demo account. Live commands require a real account.

## Dependency updates

```powershell
uv lock
uv sync --locked
```

After upgrading Typer or another CLI dependency, run every CLI help and command-surface test before accepting the lockfile.

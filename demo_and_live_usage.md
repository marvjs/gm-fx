Now that your system is fully unlocked and the Dynamic Risk Engine is in place, you have two distinct sets of commands: one for **Demo** accounts and one for **Real Money (Live)** accounts.

Before running the **Live** commands, you *must* explicitly authorize it by opening `configs/app.toml` and changing:
```toml
allow_live_account = true
```
*(Leave it as `false` if you are only running Demo commands).*

Here are the exact PowerShell commands for both environments:

### 🔵 Demo Execution Commands
Use these when logged into a Demo account on your MetaTrader 5 terminal.

**1. Start continuous automated trading (The main command):**
```powershell
uv run grandmaster-fx demo run --strategy baseline_scalper --timeframe M5
```
*(Leave this window open. It will scan, open, manage, and close trades automatically).*

**2. Check the current status (Open in a new PowerShell window):**
```powershell
uv run grandmaster-fx demo status
```
*(This shows your balance, equity, and a list of all currently open trades and their live profit).*

**3. Safely stop the bot:**
```powershell
uv run grandmaster-fx demo stop
```
*(This tells the running bot to finish its current scan and shut down safely).*

---

### 🔴 Real Money (Live) Commands
Use these when logged into a Real/Live money account on your MetaTrader 5 terminal. **Real money will be at risk.**

**1. Start continuous automated trading:**
```powershell
uv run grandmaster-fx live run --strategy baseline_scalper --timeframe M5
```

**2. Check the current status:**
```powershell
uv run grandmaster-fx live status
```

**3. Safely stop the bot:**
```powershell
uv run grandmaster-fx live stop
```

---

### Pro-Tips for Running the Bot:
* **Changing Strategies:** You can swap `--strategy baseline_scalper` with `--strategy volatility_expansion` or any other strategy configured in your `configs/experiments.toml` file.
* **Risk Engine:** Remember, your bot is currently configured in `configs/risk.toml` to risk **1.00%** of your account per trade, and it will trigger an emergency shutdown if you lose **5.00%** in a single day. You can adjust those numbers anytime before starting the `run` command!
* **Journal:** Every trade it takes (both Demo and Live) is permanently logged in `data/execution/demo_journal.jsonl` (or `live_journal.jsonl` if you run live).

Let me know if you want to tweak your risk percentages or if you are ready to let it fly!
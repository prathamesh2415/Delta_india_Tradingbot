# 5 EMA Breakout Trading Bot (Delta Exchange)

Production-ready Python bot for **BTCUSD** on **Delta Exchange India**, using **CCXT** with `DELTA_API_KEY` and `DELTA_API_SECRET`.

## Strategy

- **5 EMA Breakout** (Pine Script logic from Power of Stocks)
- **1:2 risk-reward** (`TARGET_RR=2`)
- **15m** timeframe
- **London–NY session** only (default 13:00–21:00 UTC)
- **1% risk per trade** based on **live Delta wallet balance** (not a fixed $100)

## Quick start

```bash
cd "D:\New folder"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

Copy `.env.example` values into your `.env` (you already have `DELTA_API_KEY` / `DELTA_API_SECRET`).

**Paper trade first** (recommended):

```env
PAPER_TRADING=true
ACCOUNT_EQUITY_USD=100
```

### 1. Check setup (recommended first)

```bash
python check_setup.py
```

You should see `[OK]` for API keys and Delta connection.

### 2. Start the bot

```bash
python main.py
```

Leave this terminal window **open**. The bot runs until you press `Ctrl+C`.

### 3. How to tell if it is running

| Check | What you should see |
|-------|---------------------|
| **Terminal** | Lines like `Equity: $100.00 \| Realized: ...` every ~90 seconds |
| **Log file** | `logs/trading.log` — file timestamp updates, new lines appended |
| **Telegram** | Message **"Bot Started"** when it launches |
| **Task Manager** | A `python.exe` process while the terminal is open |

Stop the bot: focus the terminal → `Ctrl+C` → you should get **"Bot Stopped"** on Telegram (if configured).

**Live trading** (real money):

```env
PAPER_TRADING=false
```

Ensure API keys have trading permission and your IP is whitelisted on Delta Exchange.

## Tests

```bash
pytest
```

Requires **≥80%** coverage (`pytest.ini`).

## Project layout

```
trading_bot/
  config.py          # DELTA_API_KEY, DELTA_API_SECRET from env
  bot.py             # Main loop
  strategy/          # 5 EMA breakout
  exchange/          # CCXT Delta India client
  risk/              # 1% sizing, daily limits
  db/                # SQLite trade log
  notifications/     # Telegram
  monitoring/        # Real-time P&L
tests/
main.py
```

## Environment variables

| Variable | Description |
|----------|-------------|
| `DELTA_API_KEY` | Delta API key (required) |
| `DELTA_API_SECRET` | Delta API secret (required) |
| `TRADING_SYMBOL` | e.g. `BTCUSD` |
| `TIMEFRAME` | e.g. `15m` |
| `ACCOUNT_EQUITY_USD` | Optional fallback only if balance API fails |
| `PAPER_TRADING` | `true` / `false` |
| `RISK_PER_TRADE_PERCENT` | Default 1 |
| `TARGET_RR` | Default 2 (1:2) |
| `TELEGRAM_BOT_TOKEN` | Optional alerts |
| `TELEGRAM_CHAT_ID` | Optional alerts |

## Profit vs fees dashboard

Shows **gross P&L**, **fees per trade**, and **net profit** (profit minus charges).

**Terminal 1 — trading bot:**
```bash
python main.py
```

**Terminal 2 — dashboard:**
```bash
pip install fastapi uvicorn
python run_dashboard.py
```

Open in browser: **http://127.0.0.1:8000/**

- Green banner = net profit after fees is positive  
- Each trade row shows entry fee, exit fee, net P&L, and whether that trade beat its fees  
- Set `TAKER_FEE_PERCENT=0.05` in `.env` to match Delta taker fees (adjust if needed)  
- Optional: `DASHBOARD_PASSWORD` in `.env` — add `?password=xxx` to the URL on EC2  

On EC2: open port **8000** in the security group (restrict to your IP).

## CI/CD (learning)

Automated **tests on every push** and optional **deploy to EC2** on `main`.

See **[deploy/CICD_LEARNING.md](deploy/CICD_LEARNING.md)** — GitHub Actions, secrets, and flow explained step by step.

```text
git push → CI (pytest) → CD (SSH to EC2, restart bot)
```

## Deploy on AWS EC2

| OS on EC2 | Guide |
|-----------|--------|
| **Windows Server** | **[deploy/DEPLOY_EC2_WINDOWS.md](deploy/DEPLOY_EC2_WINDOWS.md)** |
| Ubuntu Linux | **[deploy/DEPLOY_EC2.md](deploy/DEPLOY_EC2.md)** |

Windows quick start (on EC2 as Administrator): `cd C:\TradingBot` → `.\deploy\ec2-setup-windows.ps1`

Quick upload from Windows:

```powershell
.\deploy\upload-from-windows.ps1 -KeyPath "C:\path\to\key.pem" -Ec2Ip "YOUR_ELASTIC_IP"
```

Then on EC2: `./deploy/ec2-setup.sh` → `python check_setup.py` → `sudo systemctl start trading-bot`

## Security

- Never commit `.env` (listed in `.gitignore`)
- Rotate keys if exposed
- Start with paper trading and small size

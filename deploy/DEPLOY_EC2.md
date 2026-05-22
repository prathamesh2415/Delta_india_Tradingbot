# Deploy trading bot on AWS EC2 (Linux)

> **Your instance is Windows Server?** Use **[DEPLOY_EC2_WINDOWS.md](DEPLOY_EC2_WINDOWS.md)** instead.

This guide assumes **Ubuntu 22.04 or 24.04** on EC2 and your project in `/home/ubuntu/trading-bot`.
---

## Part 1 — AWS console (one time)

### 1. Launch / use an instance

- **AMI:** Ubuntu Server 22.04 LTS (64-bit)
- **Instance type:** `t3.micro` or `t3.small` (enough for this bot)
- **Key pair:** Create or select one (`.pem` file) — you need it to SSH
- **Security group inbound rules:**
  - SSH (22) — **only your IP** (not 0.0.0.0/0 if you can avoid it)
  - No need to open port 8000 unless you add a webhook server later

### 2. Elastic IP (recommended for Delta)

Delta India API usually requires a **whitelisted IP**.

1. EC2 → **Elastic IPs** → Allocate
2. Associate it with your instance
3. Note the IP (e.g. `3.110.xx.xx`) — this is what you whitelist on Delta

### 3. Whitelist IP on Delta Exchange

1. Log in to [Delta Exchange India](https://www.delta.exchange/)
2. API keys → manage keys → add **Elastic IP** to whitelist
3. Keys must have **trading** permission

---

## Part 2 — Copy code to EC2

### Option A — Git (best if you use GitHub)

On your laptop (in project folder, **without** committing `.env`):

```bash
git init
git add .
git commit -m "Trading bot"
# Push to a private GitHub repo, then on EC2:
```

On EC2:

```bash
ssh -i "C:\path\to\your-key.pem" ubuntu@YOUR_ELASTIC_IP
git clone https://github.com/YOUR_USER/YOUR_REPO.git trading-bot
cd trading-bot
```

### Option B — SCP from Windows (no Git)

PowerShell on your laptop:

```powershell
cd "D:\New folder"

# Copy project (exclude venv if you have one)
scp -i "C:\path\to\your-key.pem" -r `
  trading_bot main.py check_setup.py requirements-prod.txt requirements.txt `
  deploy pytest.ini README.md `
  ubuntu@YOUR_ELASTIC_IP:/home/ubuntu/trading-bot/

# Copy .env separately (secrets — never put in Git)
scp -i "C:\path\to\your-key.pem" .env ubuntu@YOUR_ELASTIC_IP:/home/ubuntu/trading-bot/.env
```

If the folder doesn't exist on EC2 first:

```bash
ssh -i "your-key.pem" ubuntu@YOUR_ELASTIC_IP "mkdir -p trading-bot"
```

---

## Part 3 — Install on EC2

SSH in:

```bash
ssh -i "C:\path\to\your-key.pem" ubuntu@YOUR_ELASTIC_IP
cd ~/trading-bot
chmod +x deploy/ec2-setup.sh
./deploy/ec2-setup.sh
```

Edit `.env` on the server if needed:

```bash
nano .env
```

Suggested for first deploy:

```env
PAPER_TRADING=true
# Remove ACCOUNT_EQUITY_USD so balance comes from Delta API
```

Verify API + balance:

```bash
source venv/bin/activate
python check_setup.py
```

You should see **Live account balance** from Delta.

---

## Part 4 — Run 24/7 with systemd

```bash
sudo systemctl start trading-bot
sudo systemctl status trading-bot
```

**Logs:**

```bash
tail -f ~/trading-bot/logs/trading.log
tail -f ~/trading-bot/logs/service.log
```

**Stop / restart:**

```bash
sudo systemctl stop trading-bot
sudo systemctl restart trading-bot
```

**After code updates:**

```bash
cd ~/trading-bot
git pull   # or re-scp files
source venv/bin/activate
pip install -r requirements-prod.txt
sudo systemctl restart trading-bot
```

---

## Part 5 — Go live

1. Confirm `check_setup.py` shows correct balance on EC2
2. Set in `.env`: `PAPER_TRADING=false`
3. `sudo systemctl restart trading-bot`
4. Confirm Telegram **"Bot Started"** with live balance

---

## Troubleshooting

| Problem | Fix |
|--------|-----|
| `AuthenticationError` / API rejected | Whitelist **Elastic IP** on Delta, not laptop IP |
| Balance $0 | API permissions; check `python check_setup.py` output |
| Bot stops after SSH exit | Use `systemctl` — do not run `python main.py` only in SSH |
| No Telegram | Check `TELEGRAM_BOT_TOKEN` / `CHAT_ID` in server `.env` |
| `Permission denied` on .pem | `icacls key.pem /inheritance:r /grant:r "%USERNAME%:R"` (Windows) |

**View service errors:**

```bash
sudo journalctl -u trading-bot -f
cat ~/trading-bot/logs/service-error.log
```

---

## Security checklist

- [ ] SSH key only (disable password login if possible)
- [ ] Security group: SSH from your IP only
- [ ] `.env` only on server, never in Git
- [ ] Rotate API keys if they were ever shared
- [ ] Start with `PAPER_TRADING=true`

---

## Quick reference

| Task | Command |
|------|---------|
| SSH | `ssh -i key.pem ubuntu@ELASTIC_IP` |
| Status | `sudo systemctl status trading-bot` |
| Logs | `tail -f ~/trading-bot/logs/trading.log` |
| Restart | `sudo systemctl restart trading-bot` |

Your laptop can be off; the bot keeps running on EC2.

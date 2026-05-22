# Deploy on AWS EC2 — Windows Server

Guide for **Windows Server 2019 / 2022** EC2. Default project path: `C:\TradingBot`

---

## Part 1 — AWS console

### Instance settings

| Setting | Value |
|--------|--------|
| AMI | **Windows Server 2022** (or 2019) |
| Instance type | `t3.small` or `t3.medium` (Windows needs more RAM than Linux) |
| Storage | 30 GB+ recommended |
| Key pair | `.pem` for optional SSH, or use **RDP password** |

### Security group (inbound)

| Port | Purpose | Source |
|------|---------|--------|
| **3389** | Remote Desktop (RDP) | **Your IP only** |
| **8000** | Profit/fees dashboard (optional) | **Your IP only** |
| 22 | OpenSSH (optional, if enabled) | Your IP only |

### Elastic IP + Delta whitelist

1. EC2 → **Elastic IPs** → Allocate → Associate with instance  
2. Whitelist that IP on [Delta Exchange API keys](https://www.delta.exchange/)  
3. Use this IP in RDP and dashboard URLs — not your home IP  

### Connect to the server

**Option A — Remote Desktop (easiest on Windows Server)**

1. EC2 → Instance → **Connect** → **RDP client** → Download `.rdp` file  
2. Or: Remote Desktop app → Computer: `YOUR_ELASTIC_IP`  
3. User: `Administrator`  
4. Password: EC2 → Connect → **Get Windows password** (decrypt with your `.pem` key)

**Option B — PowerShell from your laptop (if OpenSSH is enabled on EC2)**

```powershell
ssh -i "C:\path\to\key.pem" Administrator@YOUR_ELASTIC_IP
```

---

## Part 2 — Copy project to EC2

### Option A — RDP (simple)

1. RDP into the server  
2. Copy folder `D:\New folder` from your laptop (zip it, paste via RDP clipboard/drive, or OneDrive)  
3. Extract to `C:\TradingBot`  

### Option B — SCP (if OpenSSH Server is running on EC2)

On your **laptop** PowerShell:

```powershell
cd "D:\New folder"
.\deploy\upload-to-windows-ec2.ps1 -KeyPath "C:\path\to\key.pem" -Ec2Ip "YOUR_ELASTIC_IP" -User "Administrator"
```

### Option C — Git

On EC2 (PowerShell as Administrator):

```powershell
cd C:\
git clone https://github.com/YOUR_USER/YOUR_REPO.git TradingBot
cd C:\TradingBot
# Copy .env manually into C:\TradingBot\.env
```

---

## Part 3 — Install (run on EC2)

Open **PowerShell as Administrator** on the EC2 instance:

```powershell
cd C:\TradingBot
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.\deploy\ec2-setup-windows.ps1
```

This will:

- Install Python 3.11 (if missing)  
- Create virtual environment  
- Install `requirements-prod.txt`  
- Register **Scheduled Tasks** so bot + dashboard start on boot  

Edit `.env` on the server:

```powershell
notepad C:\TradingBot\.env
```

Set for first test:

```env
PAPER_TRADING=true
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
```

Verify API:

```powershell
cd C:\TradingBot
.\venv\Scripts\Activate.ps1
python check_setup.py
```

---

## Part 4 — Run 24/7 (Scheduled Tasks)

After setup, two tasks are registered:

| Task name | Runs |
|-----------|------|
| `TradingBot-DeltaEMA` | `python main.py` (trading) |
| `TradingBot-Dashboard` | `python run_dashboard.py` (web UI) |

**Start now:**

```powershell
Start-ScheduledTask -TaskName "TradingBot-DeltaEMA"
Start-ScheduledTask -TaskName "TradingBot-Dashboard"
```

**Status:**

```powershell
Get-ScheduledTask -TaskName "TradingBot-*" | Format-Table TaskName, State
```

**Stop:**

```powershell
Stop-ScheduledTask -TaskName "TradingBot-DeltaEMA"
Stop-ScheduledTask -TaskName "TradingBot-Dashboard"
```

**Logs:**

```powershell
Get-Content C:\TradingBot\logs\trading.log -Tail 50 -Wait
Get-Content C:\TradingBot\logs\bot-task.log -Tail 30
Get-Content C:\TradingBot\logs\dashboard-task.log -Tail 30
```

Tasks restart on failure and run again when the server reboots.

---

## Part 5 — Open dashboard

On the EC2 server browser, or from your laptop (if port 8000 is open to your IP):

```
http://YOUR_ELASTIC_IP:8000/
```

If you set `DASHBOARD_PASSWORD` in `.env`:

```
http://YOUR_ELASTIC_IP:8000/?password=your_secret
```

**Windows Firewall** on EC2 — setup script opens port 8000. If blocked, run as Administrator:

```powershell
New-NetFirewallRule -DisplayName "Trading Dashboard" -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow
```

---

## Part 6 — Go live

1. `python check_setup.py` shows correct **live balance**  
2. In `.env`: `PAPER_TRADING=false`  
3. Restart tasks:

```powershell
Stop-ScheduledTask -TaskName "TradingBot-DeltaEMA"
Start-ScheduledTask -TaskName "TradingBot-DeltaEMA"
```

4. Confirm Telegram **Bot Started**

---

## Manual run (testing, no scheduled task)

```powershell
cd C:\TradingBot
.\venv\Scripts\Activate.ps1
python main.py
```

Second window for dashboard:

```powershell
python run_dashboard.py
```

---

## Troubleshooting (Windows)

| Problem | Fix |
|--------|-----|
| Delta API rejected | Whitelist **Elastic IP** on Delta |
| Python not found | Re-run `ec2-setup-windows.ps1` or install Python from python.org |
| Script execution disabled | `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` |
| Task not running | Task Scheduler → `TradingBot-DeltaEMA` → History |
| Dashboard not loading | Security group port 8000; Windows Firewall rule |
| RDP cannot connect | Security group port 3389 from your IP |

**Re-register tasks after code update:**

```powershell
cd C:\TradingBot
.\deploy\register-windows-tasks.ps1
```

---

## Security checklist

- [ ] RDP (3389) restricted to your IP only  
- [ ] Dashboard (8000) restricted to your IP only  
- [ ] Strong Administrator password  
- [ ] `.env` only on server, not in Git  
- [ ] Start with `PAPER_TRADING=true`  

Your laptop can be off; the bot runs on Windows EC2.

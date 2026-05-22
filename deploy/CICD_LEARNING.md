# CI/CD for learning (GitHub Actions)

This project includes a simple pipeline:

```
Push code → GitHub Actions (CI) → tests pass → CD deploys to EC2 → bot restarts
```

**CI** = Continuous Integration (automated tests)  
**CD** = Continuous Deployment (automated deploy to your server)

> For **live trading with real money**, many teams run **CI on every push** but deploy to production **manually** or with approval. This setup is for **learning** — understand the flow first.

---

## What runs automatically

| Workflow | When | What it does |
|----------|------|----------------|
| **CI** (`ci.yml`) | Every push / PR | Installs Python, runs `pytest`, requires 80%+ coverage |
| **CD** (`cd.yml`) | Push to `main` / `master` | Runs CI first, then SSH to EC2 and restarts bot |

Files: `.github/workflows/ci.yml` and `.github/workflows/cd.yml`

---

## Step 1 — Put code on GitHub

On your laptop:

```powershell
cd "D:\New folder"
git init
git add .
git commit -m "Trading bot with CI/CD"
```

Create a **private** repo on GitHub, then:

```powershell
git remote add origin https://github.com/YOUR_USERNAME/trading-bot.git
git branch -M main
git push -u origin main
```

`.env` is in `.gitignore` — it will **not** be pushed (correct).

---

## Step 2 — CI only (no server yet)

After push, open GitHub → **Actions** tab → workflow **CI** should run green.

You learn:

- Tests run in a clean cloud VM every time
- Broken code is caught before deploy

---

## Step 3 — Prepare EC2 for CD

### Windows Server (your case)

1. Install **OpenSSH Server** (optional but needed for GitHub SSH deploy):
   - Settings → Apps → Optional features → **OpenSSH Server**
   - Or: `Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0`

2. Clone repo on EC2 once:

```powershell
cd C:\
git clone https://github.com/YOUR_USERNAME/trading-bot.git TradingBot
# Copy .env manually to C:\TradingBot\.env (never in Git)
.\deploy\ec2-setup-windows.ps1
```

3. Note EC2 **Elastic IP** for Delta whitelist.

---

## Step 4 — GitHub secrets (CD)

Repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

| Secret name | Example value | Purpose |
|-------------|---------------|---------|
| `EC2_HOST` | `3.110.xx.xx` | Elastic IP |
| `EC2_USER` | `Administrator` | Windows login |
| `EC2_SSH_PRIVATE_KEY` | Full `.pem` file contents | SSH key |
| `EC2_SSH_PORT` | `22` | SSH port (optional) |
| `EC2_OS` | `windows` | Use `linux` for Ubuntu EC2 |

**How to add the PEM key as secret:**

1. Open your `.pem` in Notepad
2. Copy everything including `-----BEGIN RSA PRIVATE KEY-----` lines
3. Paste into secret `EC2_SSH_PRIVATE_KEY`

---

## Step 5 — Environment protection (learning)

Repo → **Settings** → **Environments** → **New environment** → name: `production`

Optional: enable **Required reviewers** so deploy waits for your approval (good practice).

CD workflow uses `environment: production`.

---

## Step 6 — Trigger CD

```powershell
# change something small, then:
git add .
git commit -m "Test CD pipeline"
git push
```

GitHub → Actions → **CD** workflow:

1. Job **test** — runs pytest  
2. Job **deploy** — SSH to EC2 → `cd-deploy.ps1` → restarts scheduled tasks  

---

## Flow diagram

```mermaid
flowchart LR
  A[You: git push] --> B[GitHub Actions CI]
  B --> C{Tests pass?}
  C -->|No| D[Fix code]
  C -->|Yes| E[CD: SSH to EC2]
  E --> F[git pull + pip install]
  F --> G[Restart bot tasks]
  G --> H[Bot runs on EC2]
```

---

## What is NOT in CI/CD (on purpose)

| Item | Why |
|------|-----|
| `.env` / API keys | Stays only on EC2 — never in GitHub |
| Live trading toggle | You change `PAPER_TRADING` on server manually |
| Delta IP whitelist | Manual in Delta dashboard |

---

## Manual deploy (without CD)

Still valid for learning comparison:

```powershell
# On EC2
cd C:\TradingBot
git pull
.\venv\Scripts\pip install -r requirements-prod.txt
.\deploy\cd-deploy.ps1
```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| CI fails on GitHub | Run `pytest` locally; fix failing tests |
| CD: SSH connection refused | OpenSSH running on EC2; security group port 22 from GitHub IPs* |
| CD: Permission denied | Correct `EC2_USER` and PEM in secrets |
| CD: git pull fails | Clone repo on EC2 first |
| `check_setup` fails in CD | `.env` must exist on server only |

\*GitHub Actions IPs change — for strict firewalls use a **self-hosted runner** on EC2 (advanced learning topic).

---

## Next learning steps

1. Add **lint** job (`ruff` or `flake8`) in `ci.yml`  
2. Add **manual approval** on `production` environment  
3. **Self-hosted runner** on EC2 (Actions agent runs deploy locally, no SSH)  
4. **AWS CodePipeline** + CodeDeploy (AWS-native CI/CD)  

---

## Quick commands

```powershell
# Local test (same as CI)
pytest --cov=trading_bot --cov-fail-under=80

# Watch workflows
# GitHub → Actions tab
```

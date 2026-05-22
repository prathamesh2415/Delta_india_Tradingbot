# Run ONCE on Windows Server EC2 as Administrator.
# Usage: cd C:\TradingBot ; .\deploy\ec2-setup-windows.ps1

$ErrorActionPreference = "Stop"
$AppDir = if ($env:TRADING_BOT_DIR) { $env:TRADING_BOT_DIR } else { "C:\TradingBot" }

Write-Host "=== Windows EC2 setup: Trading Bot ===" -ForegroundColor Cyan
Write-Host "App directory: $AppDir"

if (-not (Test-Path $AppDir)) {
    New-Item -ItemType Directory -Path $AppDir -Force | Out-Null
}

Set-Location $AppDir
New-Item -ItemType Directory -Path "$AppDir\logs" -Force | Out-Null

# --- Python ---
function Get-PythonExe {
    $candidates = @(
        (Get-Command python -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source),
        "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe",
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "C:\Python311\python.exe",
        "C:\Python312\python.exe"
    )
    foreach ($p in $candidates) {
        if ($p -and (Test-Path $p)) { return $p }
    }
    return $null
}

$python = Get-PythonExe
if (-not $python) {
    Write-Host "Installing Python 3.11 via winget..."
    winget install Python.Python.3.11 --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" +
                [System.Environment]::GetEnvironmentVariable("Path", "User")
    $python = Get-PythonExe
    if (-not $python) {
        throw "Python not found. Install from https://www.python.org/downloads/ (check 'Add to PATH')"
    }
}
Write-Host "[OK] Python: $python"

# --- Virtual environment ---
$venvPython = "$AppDir\venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    & $python -m venv "$AppDir\venv"
}
Write-Host "[OK] Virtual environment"

& $venvPython -m pip install --upgrade pip
& $venvPython -m pip install -r "$AppDir\requirements-prod.txt"

if (-not (Test-Path "$AppDir\.env")) {
    Write-Host ""
    Write-Host "WARNING: .env not found at $AppDir\.env" -ForegroundColor Yellow
    Write-Host "Copy .env from your laptop before starting the bot."
    Write-Host ""
}

# --- Firewall: dashboard port ---
try {
    $existing = Get-NetFirewallRule -DisplayName "TradingBot-Dashboard" -ErrorAction SilentlyContinue
    if (-not $existing) {
        New-NetFirewallRule -DisplayName "TradingBot-Dashboard" `
            -Direction Inbound -LocalPort 8000 -Protocol TCP -Action Allow | Out-Null
        Write-Host "[OK] Firewall rule for port 8000"
    }
} catch {
    Write-Host "[SKIP] Could not add firewall rule (may need Administrator)" -ForegroundColor Yellow
}

# --- Scheduled tasks ---
& "$AppDir\deploy\register-windows-tasks.ps1" -AppDir $AppDir

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "  1. Ensure .env is in $AppDir"
Write-Host "  2. Whitelist Elastic IP on Delta Exchange"
Write-Host "  3. .\venv\Scripts\Activate.ps1 ; python check_setup.py"
Write-Host "  4. Start-ScheduledTask -TaskName TradingBot-DeltaEMA"
Write-Host "  5. Start-ScheduledTask -TaskName TradingBot-Dashboard"
Write-Host "  6. Dashboard: http://YOUR_ELASTIC_IP:8000/"

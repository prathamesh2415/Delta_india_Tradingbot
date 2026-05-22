# Called by GitHub Actions CD on Windows Server EC2
$ErrorActionPreference = "Stop"
$AppDir = "C:\TradingBot"
Set-Location $AppDir

Write-Host "=== CD deploy (Windows) ==="

if (Test-Path ".git") {
    git pull origin main 2>$null
    if ($LASTEXITCODE -ne 0) { git pull origin master 2>$null }
} else {
    Write-Host "No git repo — update files via CI artifact or manual copy"
}

$py = "$AppDir\venv\Scripts\python.exe"
$pip = "$AppDir\venv\Scripts\pip.exe"
if (-not (Test-Path $py)) {
    Write-Error "Run ec2-setup-windows.ps1 first (venv missing)"
}

& $pip install -r requirements-prod.txt -q
& $py check_setup.py

$tasks = @("TradingBot-DeltaEMA", "TradingBot-Dashboard")
foreach ($t in $tasks) {
    $task = Get-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
    if ($task) {
        Stop-ScheduledTask -TaskName $t -ErrorAction SilentlyContinue
        Start-Sleep -Seconds 2
        Start-ScheduledTask -TaskName $t
        Write-Host "[OK] Restarted $t"
    }
}

Write-Host "=== CD deploy done ==="

# Register Windows Scheduled Tasks for bot + dashboard (run as Administrator).
param(
    [string] $AppDir = "C:\TradingBot"
)

$ErrorActionPreference = "Stop"
$pythonExe = "$AppDir\venv\Scripts\python.exe"
if (-not (Test-Path $pythonExe)) {
    throw "venv not found at $AppDir\venv — run ec2-setup-windows.ps1 first"
}

New-Item -ItemType Directory -Path "$AppDir\logs" -Force | Out-Null

function Register-BotTask {
    param(
        [string] $TaskName,
        [string] $ScriptPath,
        [string] $LogFile
    )

    $wrapper = "$AppDir\deploy\run-python-task.ps1"
    $action = New-ScheduledTaskAction -Execute "powershell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$wrapper`" -Python `"$pythonExe`" -Script `"$ScriptPath`" -Log `"$LogFile`"" `
        -WorkingDirectory $AppDir

    $trigger = New-ScheduledTaskTrigger -AtStartup
    $settings = New-ScheduledTaskSettingsSet `
        -AllowStartIfOnBatteries `
        -DontStopIfGoingOnBatteries `
        -StartWhenAvailable `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -ExecutionTimeLimit (New-TimeSpan -Days 365)

    $principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
        -Settings $settings -Principal $principal -Description "Trading bot: $ScriptPath" | Out-Null
    Write-Host "[OK] Registered task: $TaskName"
}

Register-BotTask -TaskName "TradingBot-DeltaEMA" `
    -ScriptPath "$AppDir\main.py" `
    -LogFile "$AppDir\logs\bot-task.log"

Register-BotTask -TaskName "TradingBot-Dashboard" `
    -ScriptPath "$AppDir\run_dashboard.py" `
    -LogFile "$AppDir\logs\dashboard-task.log"

Write-Host "Start with: Start-ScheduledTask -TaskName TradingBot-DeltaEMA"

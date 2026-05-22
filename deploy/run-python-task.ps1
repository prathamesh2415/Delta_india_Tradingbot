# Wrapper for Scheduled Task — logs stdout/stderr and restarts on crash.
param(
    [Parameter(Mandatory = $true)][string] $Python,
    [Parameter(Mandatory = $true)][string] $Script,
    [Parameter(Mandatory = $true)][string] $Log
)

$ErrorActionPreference = "Continue"
$logDir = Split-Path $Log -Parent
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir -Force | Out-Null }

function Write-Log([string]$msg) {
    $line = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') $msg"
    Add-Content -Path $Log -Value $line
    Write-Host $line
}

Write-Log "Starting $Script"

while ($true) {
    try {
        & $Python $Script 2>&1 | ForEach-Object {
            Write-Log $_
        }
        Write-Log "Process exited; restarting in 15s..."
    } catch {
        Write-Log "ERROR: $_"
    }
    Start-Sleep -Seconds 15
}

# Upload project from Windows to EC2 (run in PowerShell).
# Usage:
#   .\deploy\upload-from-windows.ps1 -KeyPath "C:\keys\my.pem" -Ec2Ip "3.110.xx.xx"

param(
    [Parameter(Mandatory = $true)]
    [string] $KeyPath,
    [Parameter(Mandatory = $true)]
    [string] $Ec2Ip,
    [string] $User = "ubuntu",
    [string] $RemoteDir = "/home/ubuntu/trading-bot"
)

$ProjectRoot = Split-Path $PSScriptRoot -Parent

Write-Host "Project: $ProjectRoot"
Write-Host "Target:  ${User}@${Ec2Ip}:${RemoteDir}"

ssh -i $KeyPath "${User}@${Ec2Ip}" "mkdir -p $RemoteDir/logs"

$files = @(
    "trading_bot",
    "main.py",
    "run_dashboard.py",
    "check_setup.py",
    "requirements-prod.txt",
    "requirements.txt",
    "deploy",
    "pytest.ini",
    "README.md"
)

foreach ($item in $files) {
    $path = Join-Path $ProjectRoot $item
    if (Test-Path $path) {
        scp -i $KeyPath -r $path "${User}@${Ec2Ip}:${RemoteDir}/"
    }
}

if (Test-Path "$ProjectRoot\.env") {
    scp -i $KeyPath "$ProjectRoot\.env" "${User}@${Ec2Ip}:${RemoteDir}/.env"
    Write-Host "Uploaded .env"
} else {
    Write-Warning ".env not found — copy it manually with scp"
}

Write-Host ""
Write-Host "Done. SSH in and run:"
Write-Host "  ssh -i `"$KeyPath`" ${User}@${Ec2Ip}"
Write-Host "  cd trading-bot && ./deploy/ec2-setup.sh"

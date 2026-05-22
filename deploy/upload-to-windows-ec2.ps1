# Upload project from laptop to Windows Server EC2 (requires OpenSSH on EC2).
# Usage:
#   .\deploy\upload-to-windows-ec2.ps1 -KeyPath "C:\keys\my.pem" -Ec2Ip "3.110.xx.xx"

param(
    [Parameter(Mandatory = $true)][string] $KeyPath,
    [Parameter(Mandatory = $true)][string] $Ec2Ip,
    [string] $User = "Administrator",
    [string] $RemoteDir = "C:/TradingBot"
)

$ProjectRoot = Split-Path $PSScriptRoot -Parent
$remote = "${User}@${Ec2Ip}"

Write-Host "Creating $RemoteDir on EC2..."
ssh -i $KeyPath $remote "powershell -Command \"New-Item -ItemType Directory -Force -Path '$RemoteDir','${RemoteDir}/logs','${RemoteDir}/deploy'\""

$items = @(
    "trading_bot", "main.py", "run_dashboard.py", "check_setup.py",
    "requirements-prod.txt", "requirements.txt", "deploy", "README.md"
)

foreach ($item in $items) {
    $path = Join-Path $ProjectRoot $item
    if (Test-Path $path) {
        Write-Host "Uploading $item..."
        scp -i $KeyPath -r $path "${remote}:${RemoteDir}/"
    }
}

if (Test-Path "$ProjectRoot\.env") {
    scp -i $KeyPath "$ProjectRoot\.env" "${remote}:${RemoteDir}/.env"
    Write-Host "Uploaded .env"
} else {
    Write-Warning "No .env — copy via RDP after connect"
}

Write-Host ""
Write-Host "Next: RDP to EC2, then run as Administrator:"
Write-Host "  cd C:\TradingBot"
Write-Host "  Set-ExecutionPolicy RemoteSigned -Scope CurrentUser"
Write-Host "  .\deploy\ec2-setup-windows.ps1"

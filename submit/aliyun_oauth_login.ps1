# Aliyun OAuth login (no aliyun.env). Run in interactive terminal:
#   .\submit\aliyun_oauth_login.ps1
$Aliyun = Join-Path $env:USERPROFILE ".local\bin\aliyun.exe"
if (-not (Test-Path $Aliyun)) {
    Write-Host "Installing aliyun CLI..."
    & (Join-Path $PSScriptRoot "install_aliyun_cli.ps1")
}
Write-Host "=== Aliyun OAuth (profile: fusai-acr) ===" -ForegroundColor Cyan
Write-Host "Site Type: press Enter for CN; then sign in via browser/QR." -ForegroundColor Yellow
Write-Host ""
& $Aliyun configure --mode OAuth --profile fusai-acr
& $Aliyun configure set --profile fusai-acr --region cn-shanghai
Write-Host ""
Write-Host "Next commands:" -ForegroundColor Green
Write-Host '  .\submit\setup_acr_repos_oauth.ps1'
Write-Host '  .\submit\trigger_acr_build.ps1 -Version 0.1'

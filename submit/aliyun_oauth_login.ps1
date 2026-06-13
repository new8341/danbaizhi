# 扫码 / 浏览器登录阿里云 CLI（无需 aliyun.env AccessKey）
# 在 Cursor 终端中运行（需交互，Agent 无法代你扫码）：
#   .\submit\aliyun_oauth_login.ps1
$Aliyun = Join-Path $env:USERPROFILE ".local\bin\aliyun.exe"
if (-not (Test-Path $Aliyun)) {
    Write-Host "Installing aliyun CLI..."
    & (Join-Path $PSScriptRoot "install_aliyun_cli.ps1")
}
Write-Host "=== 阿里云 OAuth 登录（profile: fusai-acr）===" -ForegroundColor Cyan
Write-Host "按提示：Site Type 直接回车(CN)；浏览器打开后登录/扫码授权。" -ForegroundColor Yellow
Write-Host ""
& $Aliyun configure --mode OAuth --profile fusai-acr
& $Aliyun configure set --profile fusai-acr --region cn-shanghai
Write-Host ""
Write-Host "登录完成后运行：" -ForegroundColor Green
Write-Host "  .\submit\setup_acr_repos_oauth.ps1"
Write-Host "  .\submit\trigger_acr_build.ps1 -Version 0.1"

# 本机非密钥配置（Git 身份 + registry.env）
# 用法: .\submit\configure_local.ps1
$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

git config --local user.name "new8341"
git config --local user.email "new8341@users.noreply.github.com"

$registryEnv = Join-Path $PSScriptRoot "registry.env"
$registryExample = Join-Path $PSScriptRoot "registry.env.example"
if (-not (Test-Path $registryEnv)) {
    Copy-Item $registryExample $registryEnv
    Write-Host "[OK] Created submit/registry.env"
} else {
    Write-Host "[OK] submit/registry.env already exists"
}

Write-Host "[OK] Git identity:"
git config --local --get-regexp "user\."

Write-Host ""
Write-Host "Next: git push origin main  (Password = GitHub PAT)"
Write-Host "Later: docker login + build_all.ps1  (see submit/SETUP_GITHUB_ACR.md)"

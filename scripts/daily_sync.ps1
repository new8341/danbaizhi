# Daily sync: refresh scoreboard + structure check + pytest summary
param(
    [switch]$SkipTests
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Split-Path -Parent $Root)

Write-Host "=== daily_sync ===" -ForegroundColor Cyan

py -3 scripts/generate_scoreboard.py
if ($LASTEXITCODE -ne 0) { throw "generate_scoreboard failed" }

py -3 VALIDATION/check_structure.py
if ($LASTEXITCODE -ne 0) { throw "check_structure failed" }

if (-not $SkipTests) {
    py -3 -m pytest submit/tests/ -q --tb=no
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
}

Write-Host ""
Write-Host "Next: edit STATUS/DAILY_STATUS.md then tell AI: 开始执行" -ForegroundColor Green
Write-Host "Scoreboard: STATUS/SCOREBOARD.md"

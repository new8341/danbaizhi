#!/usr/bin/env pwsh
# Kick off ColabFold 3-model extra run (danbaizhi A1). Requires COLABFOLD_WSL=1 + WSL Ubuntu.
# Output: Project/processed_data/colabfold/problem_*/predictions_msa_3m/
#
# Usage:
#   .\Project\scripts\run_colabfold_extra_models.ps1 -DryRun
#   .\Project\scripts\run_colabfold_extra_models.ps1 -OnlyProblem 2

param(
    [int[]]$OnlyProblem = @(1, 2, 3),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

$env:COLABFOLD_WSL = "1"
if (-not $env:COLABFOLD_WSL_CPU) { $env:COLABFOLD_WSL_CPU = "1" }

$pyArgs = @(
    "code/run_colabfold_optional.py",
    "--problems-dir", "data",
    "--out-root", "processed_data/colabfold",
    "--models", "3",
    "--recycles", "3",
    "--predictions-subdir", "predictions_msa_3m"
)

foreach ($p in $OnlyProblem) {
    $pyArgs += @("--only-problem", "$p")
}

if ($DryRun) {
    $pyArgs += "--dry-run"
}

Write-Host "=== Danbaizhi A1: ColabFold extra models ===" -ForegroundColor Cyan
Write-Host "cwd: $Root"
Write-Host "cmd: py -3 $($pyArgs -join ' ')"

if ($DryRun) {
    py -3 @pyArgs
    exit $LASTEXITCODE
}

$logDir = Join-Path $Root "processed_data/colabfold/_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMddHHmm"
$logFile = Join-Path $logDir "extra_models_$stamp.log"

Write-Host "Logging to $logFile (background; may take many hours on CPU)"
Start-Process -FilePath "py" -ArgumentList (@("-3") + $pyArgs) `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError (Join-Path $logDir "extra_models_${stamp}.err.log") `
    -WindowStyle Hidden

Write-Host "Started background ColabFold. Tail log:" -ForegroundColor Green
Write-Host "  Get-Content -Wait $logFile"

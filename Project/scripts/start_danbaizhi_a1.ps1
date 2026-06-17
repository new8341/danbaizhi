#!/usr/bin/env pwsh
# Danbaizhi A1: install ColabFold in WSL (if needed) then run extra 3-model batch.
# Order: P3 -> P2 -> P1 (shortest first for faster first signal).

param(
    [int[]]$OnlyProblem = @(3, 2, 1),
    [switch]$SkipSetup
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

. (Join-Path $Root "scripts\colabfold_wsl_env.ps1")

$logDir = Join-Path $Root "processed_data\colabfold\_logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$stamp = Get-Date -Format "yyyyMMddHHmm"
$masterLog = Join-Path $logDir "a1_master_$stamp.log"

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $masterLog -Value $line
    Write-Host $line
}

Write-Log "=== Danbaizhi A1 pipeline start ==="
Write-Log "problems: $($OnlyProblem -join ',')"

$venvBatch = "/mnt/h/Fusai/Project/.venv_colabfold/bin/colabfold_batch"
$hasBatch = $false
if (-not $SkipSetup) {
    $check = wsl -d Ubuntu-22.04 -- bash -lc "test -x '$venvBatch' && echo OK || echo MISSING"
    $hasBatch = ($check.Trim() -eq "OK")
    Write-Log "colabfold_batch check: $check"
    if (-not $hasBatch) {
        $setupLog = Join-Path $logDir "setup_colabfold_$stamp.log"
        Write-Log "Starting WSL setup (pip install colabfold) -> $setupLog"
        Write-Log "This may take 15-30 minutes on first run + ~3.5GB weights download."
        $setupProc = Start-Process -FilePath "wsl" `
            -ArgumentList @("-d", "Ubuntu-22.04", "--", "bash", "/mnt/h/Fusai/Project/scripts/setup_colabfold_wsl.sh") `
            -RedirectStandardOutput $setupLog `
            -RedirectStandardError (Join-Path $logDir "setup_colabfold_${stamp}.err.log") `
            -PassThru -NoNewWindow
        Write-Log "setup pid=$($setupProc.Id) waiting..."
        while (-not $setupProc.HasExited) {
            Start-Sleep -Seconds 30
            if (Test-Path $setupLog) {
                $tail = Get-Content $setupLog -Tail 1 -ErrorAction SilentlyContinue
                if ($tail) { Write-Log "setup: $tail" }
            }
        }
        Write-Log "setup exit=$($setupProc.ExitCode)"
        if ($setupProc.ExitCode -ne 0) {
            Write-Error "ColabFold setup failed. See $setupLog"
        }
    }
} else {
    Write-Log "SkipSetup: assuming colabfold_batch exists"
}

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

$runLog = Join-Path $logDir "extra_models_$stamp.log"
$runErr = Join-Path $logDir "extra_models_${stamp}.err.log"
Write-Log "Starting extra models -> $runLog"
Write-Log "cmd: py -3 $($pyArgs -join ' ')"

$runProc = Start-Process -FilePath "py" -ArgumentList (@("-3") + $pyArgs) `
    -WorkingDirectory $Root `
    -RedirectStandardOutput $runLog `
    -RedirectStandardError $runErr `
    -PassThru -NoNewWindow

Write-Log "extra_models pid=$($runProc.Id)"
Write-Log "Tail: Get-Content -Wait '$runLog'"
Write-Log "Master log: $masterLog"

# Notify file for user
$notify = Join-Path $Root "processed_data\colabfold\USER_NOTIFY.txt"
@"
Danbaizhi A1 started $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
setup_log=$logDir\setup_colabfold_$stamp.log
run_log=$runLog
problems=$($OnlyProblem -join ',')
"@ | Set-Content -Path $notify -Encoding UTF8

Write-Host ""
Write-Host "A1 pipeline running. Monitor:" -ForegroundColor Green
Write-Host "  Get-Content -Wait '$runLog'"
Write-Host "  $notify"

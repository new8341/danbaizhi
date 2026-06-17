# ColabFold WSL environment for danbaizhi offline runs.
# Usage: . .\scripts\colabfold_wsl_env.ps1

$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$env:COLABFOLD_WSL = "1"
$env:COLABFOLD_WSL_DISTRO = "Ubuntu-22.04"
$env:COLABFOLD_WSL_CPU = "1"
$env:COLABFOLD_WSL_XDG_CACHE = Join-Path $Root "data\colabfold_xdg_cache"
$venvBin = "/mnt/h/Fusai/Project/.venv_colabfold/bin/colabfold_batch"
$env:COLABFOLD_WSL_BIN = $venvBin
$env:COLABFOLD_BATCH = Join-Path $Root "scripts\colabfold_batch_wsl.cmd"

New-Item -ItemType Directory -Force -Path $env:COLABFOLD_WSL_XDG_CACHE | Out-Null

Write-Host "COLABFOLD_WSL=1" -ForegroundColor Cyan
Write-Host "COLABFOLD_WSL_XDG_CACHE=$($env:COLABFOLD_WSL_XDG_CACHE)"
Write-Host "COLABFOLD_WSL_BIN=$venvBin"
if (Test-Path $env:COLABFOLD_WSL_XDG_CACHE) {
    $mb = (Get-ChildItem $env:COLABFOLD_WSL_XDG_CACHE -Recurse -File -ErrorAction SilentlyContinue |
        Measure-Object -Property Length -Sum).Sum / 1MB
    Write-Host ("cache_size_mb={0:N1}" -f $mb)
}

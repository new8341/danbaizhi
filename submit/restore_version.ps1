# Restore Fusai repo to a Git node (commit / tag / branch) without destructive defaults.
#
# Examples:
#   .\submit\restore_version.ps1 -List
#   .\submit\restore_version.ps1 -Node b7d35fc
#   .\submit\restore_version.ps1 -Node e491c22 -BranchName hotfix/baxiangfenzi
#   .\submit\restore_version.ps1 -Node HEAD~3 -RetagAcr -AcrVersion 0.1
#   .\submit\restore_version.ps1 -Node b7d35fc -ResetMain   # destructive; requires -Force

param(
    [string]$Node = "",
    [switch]$List,
    [string]$BranchName = "",
    [switch]$RetagAcr,
    [string]$AcrVersion = "0.1",
    [switch]$ResetMain,
    [switch]$Force,
    [switch]$SkipFetch
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root

function Show-RecentNodes {
    Write-Host "=== Recent commits (main) ===" -ForegroundColor Cyan
    git log main --oneline -15
    Write-Host ""
    Write-Host "=== Tags ===" -ForegroundColor Cyan
    git tag -l --sort=-creatordate | Select-Object -First 10
    Write-Host ""
    Write-Host "=== release-v0.1 -> commit ===" -ForegroundColor Cyan
    $tagCommit = git rev-list -n 1 release-v0.1 2>$null
    if ($tagCommit) {
        git log -1 --oneline $tagCommit
    } else {
        Write-Host "(tag release-v0.1 not found locally)"
    }
    Write-Host ""
    Write-Host "Per-track pins: .\submit\restore_track.ps1 -List" -ForegroundColor Yellow
    Write-Host "Per-track rollback: .\submit\restore_track.ps1 -Track danbaizhi -Node <commit> -RetagAcr" -ForegroundColor Yellow
    Write-Host "Whole-repo restore: .\submit\restore_version.ps1 -Node <commit>" -ForegroundColor Yellow
}

if ($List) {
    Show-RecentNodes
    exit 0
}

if (-not $Node) {
    Show-RecentNodes
    Write-Error "Specify -Node <commit|tag|branch> or use -List"
}

if (-not $SkipFetch) {
    git fetch origin --tags 2>$null
}

$resolved = (git rev-parse --verify "${Node}^{commit}" 2>$null)
if (-not $resolved) {
    Write-Error "Cannot resolve Git node: $Node"
}
$short = git rev-parse --short $resolved
Write-Host "Target node: $Node -> $resolved ($short)" -ForegroundColor Green
git log -1 --oneline $resolved

if ($ResetMain) {
    if (-not $Force) {
        Write-Error "ResetMain rewrites local main. Re-run with -Force if intentional."
    }
    $dirty = git status --porcelain
    if ($dirty) {
        Write-Error "Working tree not clean. Commit or stash before -ResetMain."
    }
    git checkout main
    git reset --hard $resolved
    Write-Host "Local main is now at $short (not pushed)." -ForegroundColor Yellow
    Write-Host "To publish: git push origin main  (avoid force unless you know the impact)" -ForegroundColor Yellow
} else {
    $branch = if ($BranchName) { $BranchName } else { "restore/$short" }
    git checkout -B $branch $resolved
    Write-Host "Checked out branch '$branch' at $short (main unchanged)." -ForegroundColor Green
}

if ($RetagAcr) {
    $trigger = Join-Path $Root "submit\trigger_acr_build.ps1"
    if (-not (Test-Path $trigger)) {
        Write-Error "Missing $trigger"
    }
    if ($ResetMain) {
        git push origin main
    }
    & $trigger -Version $AcrVersion -SkipPushMain
    Write-Host "Retagged release-v$AcrVersion and triggered four ACR builds." -ForegroundColor Green
}

Write-Host ""
Write-Host "Next: verify with tests, then merge to main or submit Tianchi image :$AcrVersion" -ForegroundColor Cyan

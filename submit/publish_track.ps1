# Publish ONE track only: pin HEAD -> push single ACR tag. Other tracks' pins/tags untouched.
#
# Tianchi submission unchanged:
#   crpi-.../ai4s-lee/<track>:0.1  (same as before)
#
# Examples:
#   .\submit\publish_track.ps1 -Track baxiangfenzi
#   .\submit\publish_track.ps1 -Track danbaizhi -SkipPushMain

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi")]
    [string]$Track,
    [string]$Version = "",
    [string]$Note = "",
    [switch]$SkipPushMain
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
. (Join-Path $Root "submit/track_registry.ps1")

$pins = Read-TrackPins $Root
if (-not $Version) { $Version = $pins.version }

$meta = $script:TrackMeta[$Track]

function Sync-AcrDockerfileAlias {
    param(
        [string]$Root,
        [string]$Track,
        [hashtable]$Meta
    )
    $alias = $Meta.dockerfile
    $src = Join-Path $Root "submit/Dockerfile.$Track"
    if ($Track -eq "danbaizhi") {
        $src = Join-Path $Root "submit/Dockerfile.danbaizhi"
        $alias = "Dockerfile"
    }
    if (-not (Test-Path $src)) {
        Write-Warning "No canonical dockerfile at $src — skip sync"
        return
    }
    $dst = Join-Path $Root $alias
    Copy-Item -Path $src -Destination $dst -Force
    Write-Host "Synced $src -> $alias" -ForegroundColor DarkGray
}

Sync-AcrDockerfileAlias -Root $Root -Track $Track -Meta $meta

Write-Host "=== Publish single track: $Track (image :$Version) ===" -ForegroundColor Cyan
Write-Host "Pre-publish validation..." -ForegroundColor Yellow
py -3 VALIDATION/check_structure.py
if ($LASTEXITCODE -ne 0) { throw "check_structure failed" }
py -3 -m pytest submit/tests/ -q --tb=no
if ($LASTEXITCODE -ne 0) { throw "pytest failed" }

Write-Host "Other tracks are NOT rebuilt (pins unchanged)." -ForegroundColor Green
Write-Host "Tianchi: crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/$($meta.acr_repo):$Version"
Write-Host "Output: /saisresult/$($meta.output)"

$head = git rev-parse --short HEAD
$pins.tracks.$Track.commit = $head
if ($Note) {
    $pins.tracks.$Track.note = $Note
} else {
    $pins.tracks.$Track.note = "published $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}
Write-TrackPins $Root $pins

$noteText = if ($Note) { $Note } else { "published $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
Write-BuildInfo -Root $Root -Track $Track -Commit $head -Note $noteText

Invoke-GitSafe add submit/track_pins.json submit/build_info.json
if ($meta.dockerfile) {
    Invoke-GitSafe add $meta.dockerfile
}
$dirty = git diff --cached --quiet 2>$null; if ($LASTEXITCODE -ne 0) {
    Invoke-GitSafe commit -m "chore: publish $Track build metadata ($head)"
    if (-not $SkipPushMain) {
        Invoke-GitSafe push origin main
    }
}

$commit = Resolve-GitCommit (git rev-parse HEAD)
Push-TrackTag -Track $Track -Version $Version -Commit $commit

Write-Host ""
Write-Host "Done. Only $Track tag release-v$Version-$Track was updated." -ForegroundColor Green
Write-Host "Verify build: https://cr.console.aliyun.com/repository/cn-shanghai/ai4s-lee/$($meta.acr_repo)/build"

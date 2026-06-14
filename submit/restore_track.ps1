# Per-track rollback: pin commit, restore track files, trigger single ACR build.
#
# Examples:
#   .\submit\restore_track.ps1 -List
#   .\submit\restore_track.ps1 -Track danbaizhi -Node 3f000c1 -RetagAcr
#   .\submit\restore_track.ps1 -Track baxiangfenzi -Node e491c22 -FilesOnly
#   .\submit\restore_track.ps1 -Track drugclip -PinCurrent
#   .\submit\restore_track.ps1 -Track danbaizhi -Node b7d35fc -FilesOnly -RetagAcr

param(
    [ValidateSet("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi", "")]
    [string]$Track = "",
    [string]$Node = "",
    [switch]$List,
    [switch]$FilesOnly,
    [switch]$RetagAcr,
    [switch]$PinCurrent,
    [string]$Version = "",
    [string]$Note = "",
    [switch]$SkipFetch
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
. (Join-Path $Root "submit/track_registry.ps1")

if (-not $Version) {
    $pins = Read-TrackPins $Root
    $Version = $pins.version
}

function Show-TrackStatus {
    $pins = Read-TrackPins $Root
    Write-Host "=== Per-track pins (image tag :$($pins.version)) ===" -ForegroundColor Cyan
    foreach ($name in $script:TrackOrder) {
        $entry = $pins.tracks.$name
        $tag = Get-TrackTagName -Track $name -Version $pins.version
        $short = if ($entry.commit) { $entry.commit } else { "?" }
        $line = git log -1 --oneline $short 2>$null
        Write-Host ""
        Write-Host "[$name] task$($script:TrackMeta[$name].task_id) tag=$tag" -ForegroundColor Yellow
        Write-Host "  pin: $short"
        if ($entry.note) { Write-Host "  note: $($entry.note)" }
        if ($line) { Write-Host "  git: $line" }
        Write-Host "  acr: .../ai4s-lee/$($script:TrackMeta[$name].acr_repo):$($pins.version)"
    }
    Write-Host ""
    Write-Host "Rollback one track:" -ForegroundColor Green
    Write-Host "  .\submit\restore_track.ps1 -Track danbaizhi -Node <commit> -RetagAcr"
    Write-Host "Restore track files only (monorepo stays on main):" -ForegroundColor Green
    Write-Host "  .\submit\restore_track.ps1 -Track baxiangfenzi -Node e491c22 -FilesOnly"
}

if ($List -or -not $Track) {
    Show-TrackStatus
    if (-not $Track) { exit 0 }
}

if (-not $SkipFetch) {
    git fetch origin --tags 2>$null
}

$pins = Read-TrackPins $Root
$meta = $script:TrackMeta[$Track]

if ($PinCurrent) {
    $head = git rev-parse --short HEAD
    $pins.tracks.$Track.commit = $head
    if ($Note) { $pins.tracks.$Track.note = $Note }
    else { $pins.tracks.$Track.note = "pinned at $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
    Write-TrackPins $Root $pins
    Write-Host "Pinned $Track -> $head" -ForegroundColor Green
    if (-not $RetagAcr -and -not $Node) { exit 0 }
}

$targetCommit = $null
if ($Node) {
    $targetCommit = Resolve-GitCommit $Node
    $short = git rev-parse --short $targetCommit
    Write-Host "Target $Track -> $short" -ForegroundColor Green
    git log -1 --oneline $targetCommit
    $pins.tracks.$Track.commit = $short
    if ($Note) { $pins.tracks.$Track.note = $Note }
    Write-TrackPins $Root $pins
} elseif ($RetagAcr) {
    $targetCommit = Resolve-GitCommit $pins.tracks.$Track.commit
} else {
    Write-Error "Specify -Node <commit>, -PinCurrent, or -RetagAcr"
}

if ($Node -and -not $FilesOnly -and -not $RetagAcr) {
    $RetagAcr = $true
}

if ($FilesOnly) {
    if (-not $targetCommit) {
        $targetCommit = Resolve-GitCommit $pins.tracks.$Track.commit
    }
    $paths = $meta.paths
    Write-Host "Restoring files for $Track from $(git rev-parse --short $targetCommit):" -ForegroundColor Cyan
    foreach ($rel in $paths) {
        Write-Host "  $rel"
    }
    Invoke-GitSafe checkout $targetCommit -- @paths
    Write-Host "Working tree updated for $Track paths only. Review, commit, then -RetagAcr if needed." -ForegroundColor Yellow
}

if ($RetagAcr) {
    if (-not $targetCommit) {
        $targetCommit = Resolve-GitCommit $pins.tracks.$Track.commit
    }
    Push-TrackTag -Track $Track -Version $Version -Commit $targetCommit
    Write-Host "Only $Track ACR should rebuild (requires per-track build rule in console)." -ForegroundColor Cyan
}

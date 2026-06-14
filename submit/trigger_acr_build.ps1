# Trigger ACR cloud builds — per-track tags from submit/track_pins.json
# Tag pattern: release-v<Version>-<track>
#
# IMPORTANT: -Tracks is REQUIRED. Use publish_track.ps1 for single-track updates.
param(
    [Parameter(Mandatory = $true)]
    [string[]]$Tracks,
    [string]$Version = "",
    [switch]$SkipPushMain,
    [switch]$UnifiedTag
)

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
. (Join-Path $Root "submit/track_registry.ps1")

$pins = Read-TrackPins $Root
if (-not $Version) { $Version = $pins.version }

$selected = @()
foreach ($t in $Tracks) {
    foreach ($part in ($t -split "[,\s]+")) {
        $name = $part.Trim()
        if ($name) { $selected += $name }
    }
}
$selected = $selected | Select-Object -Unique

foreach ($track in $selected) {
    if (-not $script:TrackMeta.ContainsKey($track)) {
        throw "Unknown track: $track. Valid: $($script:TrackOrder -join ', ')"
    }
}

Write-Host "=== Trigger ACR builds (per-track tags, version=$Version) ===" -ForegroundColor Cyan
Write-Host "Tracks: $($selected -join ', ') (others unchanged)" -ForegroundColor Green

if (-not (Test-Path "documen/DrugClip/benchmark/manifest.jsonl")) {
    Write-Warning "DrugClip benchmark missing — drugclip build may fail"
}

if (-not $SkipPushMain) {
    Invoke-GitSafe push origin main
}

foreach ($track in $selected) {
    $commit = Resolve-GitCommit $pins.tracks.$track.commit
    Write-Host "[$track] pin=$($pins.tracks.$track.commit)" -ForegroundColor Yellow
    Push-TrackTag -Track $track -Version $Version -Commit $commit
}

if ($UnifiedTag) {
    Write-Warning "UnifiedTag rebuilds ALL repos still listening on release-v$Version — prefer per-track tags only."
    $legacy = "release-v$Version"
    $head = git rev-parse HEAD
    $ErrorActionPreference = "Continue"
    git tag -d $legacy 2>&1 | Out-Null
    git push origin ":refs/tags/$legacy" 2>&1 | ForEach-Object { "$_" } | Write-Host
    git tag -f $legacy $head 2>&1 | ForEach-Object { "$_" } | Write-Host
    git push -f origin $legacy 2>&1 | ForEach-Object { "$_" } | Write-Host
}

Write-Host ""
Write-Host "ACR rule per repo: tags:release-v$Version-<track>  ->  image :$Version" -ForegroundColor Cyan

# Trigger ACR cloud builds — per-track tags from submit/track_pins.json
# Tag pattern: release-v<Version>-<track>  (e.g. release-v0.1-danbaizhi)
param(
    [string]$Version = "",
    [string[]]$Tracks = @(),
    [switch]$SkipPushMain,
    [switch]$UnifiedTag
)

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root
. (Join-Path $Root "submit/track_registry.ps1")

$pins = Read-TrackPins $Root
if (-not $Version) { $Version = $pins.version }

$selected = if ($Tracks.Count -gt 0) { $Tracks } else { $script:TrackOrder }

Write-Host "=== Trigger ACR builds (per-track tags, version=$Version) ===" -ForegroundColor Cyan
Write-Host "Tracks: $($selected -join ', ')"

if (-not (Test-Path "documen/DrugClip/benchmark/manifest.jsonl")) {
    Write-Warning "DrugClip benchmark missing — drugclip build may fail until benchmark is in documen/DrugClip/benchmark/"
}

if (-not $SkipPushMain) {
    Invoke-GitSafe push origin main
}

foreach ($track in $selected) {
    if (-not $pins.tracks.$track) {
        Write-Warning "Unknown track in pins: $track"
        continue
    }
    $commit = Resolve-GitCommit $pins.tracks.$track.commit
    Push-TrackTag -Track $track -Version $Version -Commit $commit
}

if ($UnifiedTag) {
    $legacy = "release-v$Version"
    $head = git rev-parse HEAD
    Write-Host "Also pushing legacy unified tag $legacy -> HEAD" -ForegroundColor Yellow
    $ErrorActionPreference = "Continue"
    git tag -d $legacy 2>&1 | Out-Null
    git push origin ":refs/tags/$legacy" 2>&1 | ForEach-Object { "$_" } | Write-Host
    git tag -f $legacy $head 2>&1 | ForEach-Object { "$_" } | Write-Host
    git push -f origin $legacy 2>&1 | ForEach-Object { "$_" } | Write-Host
}

Write-Host ""
Write-Host "Ensure each ACR repo has build rule: tags:release-v$Version-<track>" -ForegroundColor Yellow

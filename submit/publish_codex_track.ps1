# Publish a Codex-only ACR tag for ONE track.
#
# This script does not modify submit/track_pins.json and does not touch
# Cursor's release-v<version>-<track> tags. It only force-updates:
#   codex-v<version>-<track>
#
# ACR rule expected:
#   Branch/Tag: codex-v0.1-<track>
#   Context:    /
#   Dockerfile: Dockerfile(.<track>)
#   Image tag:  0.1

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi")]
    [string]$Track,
    [string]$Version = "0.1",
    [string]$Commit = "HEAD",
    [switch]$SkipValidation
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $Root
. (Join-Path $Root "submit/track_registry.ps1")

function Get-CodexTrackTagName {
    param(
        [string]$Track,
        [string]$Version
    )
    "codex-v$Version-$Track"
}

function Get-CodexAcrRepo {
    param([string]$Track)
    "codex-$Track"
}

function Push-CodexTrackTag {
    param(
        [string]$Track,
        [string]$Version,
        [string]$Commit
    )
    $tag = Get-CodexTrackTagName -Track $Track -Version $Version
    $resolved = Resolve-GitCommit $Commit

    Write-Host "Codex publish: $Track" -ForegroundColor Cyan
    Write-Host "  tag:    $tag"
    Write-Host "  commit: $(git rev-parse --short $resolved)"
    Write-Host "  image:  crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/$(Get-CodexAcrRepo $Track):$Version"

    $ErrorActionPreference = "Continue"
    git tag -d $tag 2>&1 | Out-Null
    git push origin ":refs/tags/$tag" 2>&1 | ForEach-Object { "$_" } | Write-Host
    git tag -f $tag $resolved 2>&1 | ForEach-Object { "$_" } | Write-Host
    git push -f origin $tag 2>&1 | ForEach-Object { "$_" } | Write-Host
    $code = $LASTEXITCODE
    $ErrorActionPreference = "Stop"
    if ($code -ne 0) {
        throw "git push origin $tag failed with exit code $code"
    }
    Write-Host "Pushed $tag -> $(git rev-parse --short $resolved)" -ForegroundColor Green
}

if (-not $script:TrackMeta.ContainsKey($Track)) {
    throw "Unknown track: $Track"
}

$meta = $script:TrackMeta[$Track]
Write-Host "=== Codex-only publish: $Track ===" -ForegroundColor Cyan
Write-Host "Cursor release tags are not modified." -ForegroundColor Green
Write-Host "Dockerfile for ACR: $($meta.dockerfile)"

if (-not $SkipValidation) {
    Write-Host "Pre-publish validation..." -ForegroundColor Yellow
    py -3 VALIDATION/check_structure.py
    if ($LASTEXITCODE -ne 0) { throw "check_structure failed" }
    py -3 -m pytest submit/tests/ -q --tb=no
    if ($LASTEXITCODE -ne 0) { throw "pytest failed" }
} else {
    Write-Warning "Validation skipped by -SkipValidation"
}

Push-CodexTrackTag -Track $Track -Version $Version -Commit $Commit

Write-Host ""
Write-Host "ACR rule should be:" -ForegroundColor Cyan
Write-Host "  Branch/Tag: $(Get-CodexTrackTagName -Track $Track -Version $Version)"
Write-Host "  Context:    /"
Write-Host "  Dockerfile: $($meta.dockerfile)"
Write-Host "  Image tag:  $Version"

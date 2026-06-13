# Trigger ACR cloud builds for all four tracks (tag release-v$Version).
# Requires: four ACR repos bound to GitHub new8341/danbaizhi with tags:release-v$version
param(
    [string]$Version = "0.1",
    [switch]$SkipPushMain
)

$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

function Invoke-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$GitArgs)
    $prev = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    & git @GitArgs 2>&1 | ForEach-Object { "$_" } | Write-Host
    $code = $LASTEXITCODE
    $ErrorActionPreference = $prev
    if ($code -ne 0) {
        throw "git $($GitArgs -join ' ') failed with exit code $code"
    }
}

$tag = "release-v$Version"
Write-Host "=== Trigger ACR builds for all tracks (tag=$tag) ===" -ForegroundColor Cyan

if (-not (Test-Path "documen/DrugClip/benchmark/manifest.jsonl")) {
    Write-Warning "DrugClip benchmark missing — drugclip build may fail until benchmark is in documen/DrugClip/benchmark/"
}

if (-not $SkipPushMain) {
    Invoke-Git push origin main
}

Invoke-Git tag -d $tag 2>$null
Invoke-Git push origin ":refs/tags/$tag" 2>$null
Invoke-Git tag -f $tag
Invoke-Git push origin $tag

Write-Host ""
Write-Host "Pushed tag $tag — check each ACR repo build log:" -ForegroundColor Green
@(
    "danbaizhi",
    "drugclip",
    "baxiangfenzi",
    "shenjingsuanzi"
) | ForEach-Object {
    Write-Host "  https://cr.console.aliyun.com/repository/cn-shanghai/ai4s-lee/$_/build"
}

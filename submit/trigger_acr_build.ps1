# 触发四个 ACR 仓库同步云端构建
# 前提：四个仓库均已绑定 GitHub new8341/danbaizhi，构建规则均为 tags:release-v$version
param(
    [string]$Version = "0.1",
    [switch]$SkipPushMain
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$tag = "release-v$Version"
Write-Host "=== Trigger ACR builds for all tracks (tag=$tag) ===" -ForegroundColor Cyan

if (-not (Test-Path "documen/DrugClip/benchmark/manifest.jsonl")) {
    Write-Warning "DrugClip benchmark missing at documen/DrugClip/benchmark/ — drugclip ACR build will FAIL until you unzip benchmark.zip there."
}

if (-not $SkipPushMain) {
    git push origin main
}

git tag -d $tag 2>$null | Out-Null
git push origin ":refs/tags/$tag" 2>$null | Out-Null
git tag $tag
git push origin $tag

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

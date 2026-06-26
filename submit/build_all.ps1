# Build all Fusai track images (PowerShell).
# Usage:
#   .\submit\build_all.ps1
#   .\submit\build_all.ps1 -Tag 0.2 -Push
#   .\submit\build_all.ps1 -Tracks danbaizhi,drugclip
param(
    [string]$Tag = "",
    [switch]$Push,
    [string[]]$Tracks = @("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi"),
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

$pyArgs = @("submit/build_all.py", "--tracks") + $Tracks
if ($Tag) { $pyArgs += @("--tag", $Tag) }
if ($Push) { $pyArgs += "--push" }
if ($DryRun) { $pyArgs += "--dry-run" }

py -3 @pyArgs

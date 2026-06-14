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
$head = git rev-parse --short HEAD

Write-Host "=== Publish single track: $Track (image :$Version) ===" -ForegroundColor Cyan
Write-Host "Other tracks are NOT rebuilt (pins unchanged)." -ForegroundColor Green
Write-Host "Tianchi: crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/$($meta.acr_repo):$Version"
Write-Host "Output: /saisresult/$($meta.output)"

if (-not $SkipPushMain) {
    Invoke-GitSafe push origin main
}

$pins.tracks.$Track.commit = $head
if ($Note) {
    $pins.tracks.$Track.note = $Note
} else {
    $pins.tracks.$Track.note = "published $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
}
Write-TrackPins $Root $pins

$commit = Resolve-GitCommit $head
Push-TrackTag -Track $Track -Version $Version -Commit $commit

Write-Host ""
Write-Host "Done. Only $Track tag release-v$Version-$Track was updated." -ForegroundColor Green
Write-Host "Verify build: https://cr.console.aliyun.com/repository/cn-shanghai/ai4s-lee/$($meta.acr_repo)/build"

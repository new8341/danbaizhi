# Shared track metadata for per-track pin / restore / ACR trigger.

$script:TrackOrder = @(
    "danbaizhi",
    "drugclip",
    "baxiangfenzi",
    "shenjingsuanzi"
)

$script:TrackMeta = @{
    danbaizhi = @{
        task_id   = "3"
        acr_repo  = "danbaizhi"
        dockerfile = "Dockerfile"
        output    = "submission.zip"
        paths     = @(
            "Dockerfile",
            "submit/Dockerfile",
            "submit/Dockerfile.danbaizhi",
            "submit/tracks/danbaizhi.py",
            "Project"
        )
    }
    drugclip = @{
        task_id   = "1"
        acr_repo  = "drugclip"
        dockerfile = "Dockerfile.drugclip"
        output    = "result.zip"
        paths     = @(
            "Dockerfile.drugclip",
            "submit/Dockerfile.drugclip",
            "submit/tracks/drugclip.py"
        )
    }
    baxiangfenzi = @{
        task_id   = "2"
        acr_repo  = "baxiangfenzi"
        dockerfile = "Dockerfile.baxiangfenzi"
        output    = "result.zip"
        paths     = @(
            "Dockerfile.baxiangfenzi",
            "submit/Dockerfile.baxiangfenzi",
            "submit/tracks/baxiangfenzi.py",
            "submit/tracks/baxiangfenzi_agent"
        )
    }
    shenjingsuanzi = @{
        task_id   = "4"
        acr_repo  = "shenjingsuanzi"
        dockerfile = "Dockerfile.shenjingsuanzi"
        output    = "submission.zip"
        paths     = @(
            "Dockerfile.shenjingsuanzi",
            "submit/Dockerfile.shenjingsuanzi",
            "submit/tracks/shenjingsuanzi.py"
        )
    }
}

function Get-TrackPinsPath {
    param([string]$Root)
    Join-Path $Root "submit/track_pins.json"
}

function Read-TrackPins {
    param([string]$Root)
    $path = Get-TrackPinsPath $Root
    if (-not (Test-Path $path)) {
        throw "Missing $path"
    }
    Get-Content $path -Raw -Encoding UTF8 | ConvertFrom-Json
}

function Write-TrackPins {
    param(
        [string]$Root,
        [object]$Pins
    )
    $path = Get-TrackPinsPath $Root
    ($Pins | ConvertTo-Json -Depth 6) + "`n" | Set-Content -Path $path -Encoding UTF8 -NoNewline
}

function Write-BuildInfo {
    param(
        [string]$Root,
        [string]$Track,
        [string]$Commit,
        [string]$Note = ""
    )
    $path = Join-Path $Root "submit/build_info.json"
    $info = [ordered]@{
        track     = $Track
        commit    = $Commit
        published = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        note      = $Note
    }
    ($info | ConvertTo-Json -Depth 4) + "`n" | Set-Content -Path $path -Encoding UTF8 -NoNewline
}

function Get-TrackTagName {
    param(
        [string]$Track,
        [string]$Version
    )
    "release-v$Version-$Track"
}

function Resolve-GitCommit {
    param([string]$Node)
    $resolved = git rev-parse --verify "${Node}^{commit}" 2>$null
    if (-not $resolved) {
        throw "Cannot resolve Git node: $Node"
    }
    return $resolved
}

function Invoke-GitSafe {
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

function Push-TrackTag {
    param(
        [string]$Track,
        [string]$Version,
        [string]$Commit
    )
    $tag = Get-TrackTagName -Track $Track -Version $Version
    $ErrorActionPreference = "Continue"
    git tag -d $tag 2>&1 | Out-Null
    git push origin ":refs/tags/$tag" 2>&1 | ForEach-Object { "$_" } | Write-Host
    git tag -f $tag $Commit 2>&1 | ForEach-Object { "$_" } | Write-Host
    git push -f origin $tag 2>&1 | ForEach-Object { "$_" } | Write-Host
    if ($LASTEXITCODE -ne 0) {
        throw "git push origin $tag failed with exit code $LASTEXITCODE"
    }
    Write-Host "Pushed $tag -> $(git rev-parse --short $Commit)" -ForegroundColor Green
    Write-Host "  https://cr.console.aliyun.com/repository/cn-shanghai/ai4s-lee/$($script:TrackMeta[$Track].acr_repo)/build"
}

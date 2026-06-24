# Local docker build + push with LLM keys from submit/llm.env (gitignored).
# Personal ACR cloud build cannot pass --build-arg; use this when Docker Desktop works.
#
# Usage:
#   .\submit\publish_with_llm.ps1 -Track danbaizhi -Push
#   .\submit\publish_with_llm.ps1 -Track all -Push

param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi", "all")]
    [string]$Track,
    [switch]$Push,
    [string]$Tag = "0.1"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
. (Join-Path $Root "submit/track_registry.ps1")

$envFile = Join-Path $PSScriptRoot "llm.env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $PSScriptRoot "llm.env.example") $envFile
    throw "Fill submit/llm.env then rerun (file is gitignored)."
}

$llm = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $llm[$matches[1].Trim()] = $matches[2].Trim()
    }
}

$regFile = Join-Path $PSScriptRoot "registry.env"
if (-not (Test-Path $regFile)) {
    Copy-Item (Join-Path $PSScriptRoot "registry.env.example") $regFile
}
$reg = @{}
Get-Content $regFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.+)$') { $reg[$matches[1].Trim()] = $matches[2].Trim() }
}

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    throw "Docker daemon not running. Start Docker Desktop or use ACR cloud build (keys stay empty)."
}

function Build-TrackImage {
    param([string]$Name)
    $meta = $script:TrackMeta[$Name]
    $prefix = switch ($Name) {
        "baxiangfenzi" { "BAXIANG" }
        "danbaizhi" { "DANBAIZHI" }
        "drugclip" { "DRUGCLIP" }
        "shenjingsuanzi" { "SHENJING" }
    }
    $df = Join-Path $Root $meta.dockerfile
    if ($Name -eq "danbaizhi") { $df = Join-Path $Root "submit/Dockerfile.danbaizhi" }
    $image = "$($reg['REGISTRY'])/$($reg['NAMESPACE'])/$($meta.acr_repo):$Tag"
    $args = @(
        "build", "-f", $df,
        "--build-arg", "${prefix}_LLM_API_KEY=$($llm["${prefix}_LLM_API_KEY"])",
        "--build-arg", "${prefix}_LLM_BASE_URL=$($llm["${prefix}_LLM_BASE_URL"])",
        "--build-arg", "${prefix}_LLM_MODEL=$($llm["${prefix}_LLM_MODEL"])",
        "-t", $image, "."
    )
    Write-Host "=== docker $($args -join ' ') ===" -ForegroundColor Cyan
    & docker @args
    if ($LASTEXITCODE -ne 0) { throw "docker build failed for $Name" }
    if ($Push) {
        docker push $image
        if ($LASTEXITCODE -ne 0) { throw "docker push failed for $Name" }
    }
    Write-Host "[OK] $image" -ForegroundColor Green
}

$tracks = if ($Track -eq "all") { @("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi") } else { @($Track) }
foreach ($t in $tracks) { Build-TrackImage $t }

Write-Host "Done. Tianchi: crpi-.../ai4s-lee/<track>:$Tag"

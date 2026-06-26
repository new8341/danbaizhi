# Danbaizhi: build, local test, optional push to ACR
# Usage:
#   .\submit\publish_danbaizhi.ps1
#   .\submit\publish_danbaizhi.ps1 -Push
#   .\submit\publish_danbaizhi.ps1 -Tag 0.2 -Push
param(
    [string]$Tag = "",
    [switch]$Push,
    [switch]$SkipTest
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

# Load tag from registry.env
$envFile = Join-Path $PSScriptRoot "registry.env"
if (-not (Test-Path $envFile)) {
    Copy-Item (Join-Path $PSScriptRoot "registry.env.example") $envFile
}
$reg = @{}
Get-Content $envFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.+)$') { $reg[$matches[1].Trim()] = $matches[2].Trim() }
}
if (-not $Tag) { $Tag = $reg["TAG"] }
$image = "$($reg['REGISTRY'])/$($reg['NAMESPACE'])/danbaizhi:$Tag"

Write-Host "Image: $image"

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Error "Docker daemon not running. Start Docker Desktop and retry."
}

Write-Host "[1/4] docker build ..."
docker build -f submit/Dockerfile.danbaizhi -t $image .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

if (-not $SkipTest) {
    Write-Host "[2/4] docker run (local test) ..."
    $outDir = Join-Path $PSScriptRoot "_local_saisresult"
    New-Item -ItemType Directory -Force -Path $outDir | Out-Null
    docker run --rm `
        -v "${Root}/documen/Danbaizhi:/saisdata:ro" `
        -v "${outDir}:/saisresult" `
        $image
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    $zip = Join-Path $outDir "output.zip"
    if (-not (Test-Path $zip)) { Write-Error "Missing $zip after container run" }
    Write-Host "[OK] $zip ($((Get-Item $zip).Length) bytes)"
} else {
    Write-Host "[2/4] skipped local test"
}

if ($Push) {
    Write-Host "[3/4] docker login (interactive) ..."
    docker login $reg["REGISTRY"]
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    Write-Host "[4/4] docker push ..."
    docker push $image
} else {
    Write-Host "[3/4] skip push (use -Push to upload)"
    Write-Host "Tianchi image path: $image"
}

Write-Host "Done."

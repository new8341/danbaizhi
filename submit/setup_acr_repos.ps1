# Create missing ACR personal-edition repos (drugclip, baxiangfenzi, shenjingsuanzi).
# Requires: aliyun CLI + submit/aliyun.env (see aliyun.env.example)
param(
    [string]$EnvFile = (Join-Path $PSScriptRoot "aliyun.env")
)

$ErrorActionPreference = "Stop"
$Aliyun = Join-Path $env:USERPROFILE ".local\bin\aliyun.exe"
if (-not (Test-Path $Aliyun)) {
    Write-Error "aliyun CLI not found at $Aliyun. Run: .\submit\install_aliyun_cli.ps1"
}

if (-not (Test-Path $EnvFile)) {
    Write-Error "Missing $EnvFile — copy aliyun.env.example and fill AccessKey."
}

Get-Content $EnvFile | ForEach-Object {
    if ($_ -match '^\s*([^#=]+)=(.*)$') {
        $name = $matches[1].Trim()
        $val = $matches[2].Trim().Trim('"').Trim("'")
        Set-Item -Path "env:$name" -Value $val
    }
}

$region = $env:ACR_REGION
$instance = $env:ACR_INSTANCE_ID
$ns = $env:ACR_NAMESPACE

& $Aliyun configure set `
    --profile fusai-acr `
    --mode AK `
    --access-key-id $env:ALIBABA_CLOUD_ACCESS_KEY_ID `
    --access-key-secret $env:ALIBABA_CLOUD_ACCESS_KEY_SECRET `
    --region $region | Out-Null

$repos = @(
    @{ Name = "drugclip"; Summary = "AI4S task1 DrugClip" },
    @{ Name = "baxiangfenzi"; Summary = "AI4S task2 targeted molecule" },
    @{ Name = "shenjingsuanzi"; Summary = "AI4S task4 neural operator PDE" }
)

foreach ($r in $repos) {
    $body = @{
        InstanceId = $instance
        RepoNamespaceName = $ns
        RepoName = $r.Name
        RepoType = "PRIVATE"
        Summary = $r.Summary
    } | ConvertTo-Json -Compress

    Write-Host "Creating repo $($r.Name) ..." -ForegroundColor Cyan
    $out = & $Aliyun cr CreateRepository --force --profile fusai-acr --region $region --body $body 2>&1 | Out-String
    if ($out -match "IsSuccess.*true|RepoId|already exist|REPO_ALREADY_EXIST") {
        Write-Host "  OK: $($r.Name)" -ForegroundColor Green
    } else {
        Write-Host $out
        Write-Warning "  Check console if repo $($r.Name) already exists or needs manual create."
    }
}

Write-Host ""
Write-Host "Next: bind GitHub + build rules in console for each new repo (see MULTI_TRACK_ACR.md)." -ForegroundColor Yellow
Write-Host "Then: .\submit\trigger_acr_build.ps1 -Version 0.1"

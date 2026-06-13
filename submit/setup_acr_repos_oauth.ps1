# Create ACR repos using OAuth profile fusai-acr (after aliyun_oauth_login.ps1)
$ErrorActionPreference = "Stop"
$Aliyun = Join-Path $env:USERPROFILE ".local\bin\aliyun.exe"
$region = "cn-shanghai"
$instance = "crpi-i14uo4x5tmwyoptf"
$ns = "ai4s-lee"

$profiles = & $Aliyun configure list 2>&1 | Out-String
if ($profiles -notmatch "fusai-acr") {
    Write-Error "Profile fusai-acr not found. Run: .\submit\aliyun_oauth_login.ps1"
}

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

    Write-Host "Creating $($r.Name) ..." -ForegroundColor Cyan
    $out = & $Aliyun cr CreateRepository --force --profile fusai-acr --region $region --body $body 2>&1 | Out-String
    Write-Host $out
}

Write-Host ""
Write-Host "Done. Configure GitHub + build rules in console if repos are new." -ForegroundColor Green
Write-Host "Then: .\submit\trigger_acr_build.ps1 -Version 0.1"

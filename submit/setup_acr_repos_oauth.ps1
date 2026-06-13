# Personal-edition ACR: CreateRepository API is NOT supported — use console instead.
# OAuth login still useful for future enterprise API; repos must be created in console.
$ErrorActionPreference = "Continue"
Write-Host ""
Write-Host "=== ACR personal edition: create repos in CONSOLE (API not supported) ===" -ForegroundColor Yellow
Write-Host ""
Write-Host "Open: https://cr.console.aliyun.com/" -ForegroundColor Cyan
Write-Host "Region: East China 2 (Shanghai) | Namespace: ai4s-lee | GitHub: new8341/danbaizhi"
Write-Host ""
Write-Host "Create 3 private repos (copy settings from danbaizhi):" -ForegroundColor Green
Write-Host ""
$repos = @(
    @{ Name = "drugclip"; Dockerfile = "submit/Dockerfile.drugclip" },
    @{ Name = "baxiangfenzi"; Dockerfile = "submit/Dockerfile.baxiangfenzi" },
    @{ Name = "shenjingsuanzi"; Dockerfile = "submit/Dockerfile.shenjingsuanzi" }
)
foreach ($r in $repos) {
    Write-Host "  [$($r.Name)]"
    Write-Host "    Dockerfile: $($r.Dockerfile)"
    Write-Host "    Context: /"
    Write-Host "    Rule: tags:release-v`$version | tag: `$version"
    Write-Host "    Overseas build: OFF | Auto-build: ON"
    Write-Host "    URL: https://cr.console.aliyun.com/repository/cn-shanghai/ai4s-lee/$($r.Name)/build"
    Write-Host ""
}
Write-Host "After all 3 repos exist, run:" -ForegroundColor Green
Write-Host '  .\submit\trigger_acr_build.ps1 -Version 0.1'
Write-Host ""
Write-Host "Note: OAuth profile region was fixed to cn-shanghai (you had entered gengfu369 by mistake)." -ForegroundColor DarkYellow

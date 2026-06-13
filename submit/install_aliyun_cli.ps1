$bin = Join-Path $env:USERPROFILE ".local\bin"
New-Item -ItemType Directory -Path $bin -Force | Out-Null
$zip = Join-Path $env:TEMP "aliyun-cli-windows.zip"
$url = "https://github.com/aliyun/aliyun-cli/releases/download/v3.3.23/aliyun-cli-windows-3.3.23-amd64.zip"
Write-Host "Downloading $url"
Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
Expand-Archive -Path $zip -DestinationPath $env:TEMP\aliyun-cli-extract -Force
Copy-Item "$env:TEMP\aliyun-cli-extract\aliyun.exe" (Join-Path $bin "aliyun.exe") -Force
& (Join-Path $bin "aliyun.exe") version

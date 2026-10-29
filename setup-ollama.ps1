param([string]$Version = 'v0.40.5')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) { throw 'Once .\setup.ps1 calistirin.' }
$runtimePath = Join-Path $PSScriptRoot 'runtime'
$manifestPath = Join-Path $runtimePath 'ollama-install.json'
if (-not (Test-Path -LiteralPath $manifestPath)) {
    $release = Invoke-RestMethod -Uri "https://api.github.com/repos/ollama/ollama/releases/tags/$Version"
    $asset = $release.assets | Where-Object name -EQ 'ollama-windows-amd64.zip' | Select-Object -First 1
    if (-not $asset -or $asset.digest -notlike 'sha256:*') { throw 'Resmi paket ozeti bulunamadi.' }
    New-Item -ItemType Directory -Path $runtimePath -Force | Out-Null
    $archivePath = Join-Path $runtimePath "ollama-$Version.zip"
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $archivePath
    $checksum = (Get-FileHash -LiteralPath $archivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($checksum -ne $asset.digest.Substring(7)) { throw 'Paket SHA256 dogrulamasi basarisiz.' }
    $installPath = Join-Path $runtimePath "ollama-$Version"
    Expand-Archive -LiteralPath $archivePath -DestinationPath $installPath -Force
    @{version=$Version;executable=(Join-Path $installPath 'ollama.exe');sha256=$checksum;source=$asset.browser_download_url} |
        ConvertTo-Json | Set-Content -LiteralPath $manifestPath -Encoding UTF8
}
& $projectPython scripts/ollama_runtime.py --pull
exit $LASTEXITCODE

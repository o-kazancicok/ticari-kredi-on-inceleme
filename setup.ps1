param([string]$PythonPath, [switch]$Agent)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    $pythonArguments = @()
    if ($PythonPath) { $basePython = $PythonPath }
    elseif (Get-Command py -ErrorAction SilentlyContinue) {
        $basePython = 'py'
        $pythonArguments = @('-3')
    } else {
        $basePython = 'python'
        $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
        if (-not $pythonCommand -or $pythonCommand.Source -like '*\Microsoft\WindowsApps\*') {
            throw 'Python 3.11+ kurun veya -PythonPath ile gercek python.exe yolunu belirtin.'
        }
    }
    & $basePython @pythonArguments -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.11 veya ustu gerekiyor.' }
    & $basePython @pythonArguments -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Python sanal ortami olusturulamadi.' }
}
$requirements = if (Test-Path -LiteralPath 'requirements-lock.txt') { 'requirements-lock.txt' } else { 'requirements-dev.txt' }
& $projectPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) { throw 'Bagimliliklar kurulamadi.' }
if ($Agent) {
    & $projectPython -m pip install -r requirements-agent.txt
    if ($LASTEXITCODE -ne 0) { throw 'Agent bagimliliklari kurulamadi.' }
}
if (-not (Test-Path -LiteralPath '.env')) {
    Copy-Item -LiteralPath '.env.example' -Destination '.env'
}
& $projectPython -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Bagimlilik uyumsuzlugu bulundu.' }
Write-Host 'Kurulum tamamlandi. Kontrol: .\start.ps1 -Check; Baslatma: .\start.ps1'

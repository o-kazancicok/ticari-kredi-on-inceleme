param(
    [ValidateSet('demo', 'agent')][string]$Mode,
    [int]$Port,
    [switch]$Check,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$projectPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $projectPython)) {
    throw 'Python ortami bulunamadi. Once .\setup.ps1 calistirin.'
}
$effectiveMode = if ($Mode) { $Mode } else {
    & $projectPython -c "from kredi.environment import load_environment; import os; load_environment(); print(os.getenv('KREDI_MODE','demo'))"
}
if ($LASTEXITCODE -and -not $Mode) { throw 'Ortam ayarlari okunamadi.' }
if ($effectiveMode -eq 'agent' -and -not $Check) {
    & $projectPython scripts/ollama_runtime.py
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
$appArguments = @('app.py')
if ($Mode) { $appArguments += @('--mode', $Mode) }
if ($PSBoundParameters.ContainsKey('Port')) { $appArguments += @('--port', "$Port") }
if ($Check) { $appArguments += '--check' }
elseif (-not $NoBrowser) { $appArguments += '--open-browser' }
& $projectPython @appArguments
exit $LASTEXITCODE
